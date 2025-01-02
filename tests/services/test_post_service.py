import pytest
from unittest.mock import AsyncMock
from pytest_mock import MockFixture

from app.services.post_service import HeaderPostsService
from app.services.common.structures import GenerateStructureService
from app.schemas import NewPostHeaderInput
from app.models import Categories, EventsHeaders

class DatabaseSession:
    def __init__(self, mocker: MockFixture):
        self.mock = mocker
        self.session = self.mock.Mock()

@pytest.fixture
def mock_expected_output_succeed(mock_location_succeed):
    return {
        "status": "success",
        "details": 
            (
            mock_location_succeed.get("point"), 
            mock_location_succeed.get("address")
            ),
    }

@pytest.fixture
def mock_expected_output_error():
    return {
        "status": "error",
        "details": ""
    }

@pytest.fixture
def mock_header_input():
    return NewPostHeaderInput(
        id=-1,
        title="Test",
        description="Test description",
        location="C/Test 12344",
        category=2,
        status=0
    )

@pytest.fixture
def mock_location_succeed():
    return {
            "status": "success",
            "point": (41.456733, 2.67473),
            "address": "C/Test, 1234",
        }

class TestHeaderPostService:
    
    @pytest.fixture
    def db_session(self, mocker: MockFixture):
        return DatabaseSession(mocker).session
    
    @pytest.fixture
    def mock_fetched_category(self):
        return Categories(
            id=1,
            code="cat.01",
            name="Cat Test"
        )
    
    @pytest.fixture
    def mock_header_record(self):
        return EventsHeaders(
            id=1,
            title="Test",
            description="This is a test",
            address="C/Test, 123",
            coordinates="41.62724, 2.4848944",
            img="https://path.com/image1",
            img2="https://path.com/image2",
            owner_id=1,
            category=2,
            created_at="1734607775.017824",
            status=1,
            score=0
        )
    
    @pytest.fixture
    def mock_header_record_dict(self, mock_header_record):
        return {
                column.name: getattr(mock_header_record, column.name)
                for column in mock_header_record.__table__.columns
                }
    
    @pytest.mark.asyncio
    async def test_validate_header_inputs_succeed(
        self, 
        mocker: MockFixture, 
        db_session, 
        mock_header_input, 
        mock_fetched_category,
        mock_location_succeed, 
        mock_expected_output_succeed
        ):
        
        mocker.patch.object(HeaderPostsService, "_validate_header_basic_fields", return_value=None)
        mocker.patch.object(HeaderPostsService, "_validate_location", return_value=mock_location_succeed)
        db_session.query().filter().first.return_value=mock_fetched_category
        
        result = await HeaderPostsService.validate_header_inputs(db_session, mock_header_input)
        
        assert result == mock_expected_output_succeed
    
    @pytest.mark.parametrize("categoryError, _validate_header_basic_fieldsError, _validate_locationError, message", [
        (True, False, False, "Category not found"),
        (False, True, False, ["Title field is empty", "Description field is empty", "Category field is empty"]),
        (False, False, True, "A location must be provided"),
    ])
    @pytest.mark.asyncio
    async def test_validate_header_inputs_errors(
        self, 
        mocker: MockFixture, 
        db_session, 
        mock_header_input, 
        mock_fetched_category,
        mock_location_succeed, 
        mock_expected_output_error,
        message,
        categoryError,
        _validate_header_basic_fieldsError,
        _validate_locationError
        ):
        
        mock_validation_error = None
        mock_location_error = mock_location_succeed
        
        if categoryError:
            mock_fetched_category = None
        if _validate_header_basic_fieldsError:
            mock_validation_error = mock_expected_output_error
            mock_validation_error["details"] = message
        if _validate_locationError:
            mock_location_error = mock_expected_output_error
            mock_location_error["details"] = message
            
        mocker.patch.object(HeaderPostsService, "_validate_header_basic_fields", return_value=mock_validation_error)
        mocker.patch.object(HeaderPostsService, "_validate_location", return_value=mock_location_error)
        mock_expected_output_error["details"] = message
        db_session.query().filter().first.return_value=mock_fetched_category
        
        result = await HeaderPostsService.validate_header_inputs(db_session, mock_header_input)
        
        assert result == mock_expected_output_error
    
    @pytest.mark.parametrize("fetchedRecord, message", [
        (True, "Found pending headers"),
        (False, "No pending headers")
    ])
    def test_fetch_pending_header(
        self, 
        db_session, 
        mock_expected_output_succeed,
        mock_header_record,
        fetchedRecord,
        message
        ):
        
        if not fetchedRecord:
            mock_header_record=None
        mock_expected_output_succeed["details"] = (message, 
                                                   GenerateStructureService.generate_header_structure(mock_header_record)
                                                   )
            
        db_session.query().filter().first.return_value = mock_header_record
        
        result = HeaderPostsService.fetch_pending_headers(db_session, 1)

        assert result == mock_expected_output_succeed
    
    @pytest.mark.asyncio
    async def test_process_header_succeed(
        self,
        db_session,
        mock_header_input,
        mocker: MockFixture,
        mock_location_succeed,
        mock_expected_output_succeed,
        mock_header_record_dict
    ):
        mocker.patch.object(HeaderPostsService, "_validate_header_basic_fields", return_value=None)
        mocker.patch.object(HeaderPostsService, "_validate_header_basic_fields", return_value=mock_location_succeed)
        mock_expected_output_succeed["details"] = {
            "message": "Approved header", 
            "header": mock_header_record_dict
        }
        mocker.patch.object(HeaderPostsService, "_add_header", return_value=mock_header_record_dict)
        
        result = await HeaderPostsService.process_header(db_session, 1, mock_header_input)
        
        assert result == mock_expected_output_succeed
    
class TestHeaderPostServiceHelpers:
    
    def test__validate_header_basic_fields_succeed(
        self, 
        mock_header_input
        ):
        
        result = HeaderPostsService._validate_header_basic_fields(mock_header_input)
        
        assert result == None  # noqa: E711

    @pytest.mark.parametrize("field_name, field_value, message", [
        ("title", "", "Title field is empty"),
        ("description", "", "Description field is empty"),
        ("category", None, "Category field is empty")
    ])
    def test__validate_header_basic_fields_errors(
        self,
        mock_header_input,
        field_name,
        field_value,
        message,
        mock_expected_output_error
    ):
        setattr(mock_header_input, field_name, field_value)
        mock_expected_output_error["details"] = message
        
        result = HeaderPostsService._validate_header_basic_fields(mock_header_input)
        
        assert result == mock_expected_output_error
    
    
    @pytest.mark.parametrize("isAddress, location_value", [
        (True, "C/Test 1234"),
        (False, [41.73548345343, 2.5423642846])
    ])
    @pytest.mark.asyncio
    async def test__validate_location_succeed(
        self, 
        mock_header_input,
        mocker: MockFixture,
        mock_location_succeed,
        isAddress,
        location_value
        ):
        
        if not isAddress:
            setattr(mock_header_input, "location", location_value)
            
        mocker.patch("app.utils.maps_utils.fetch_geocode_data", return_value=mock_location_succeed)
        mocker.patch("app.utils.maps_utils.fetch_reverse_geocode_data", return_value=mock_location_succeed)
    
        result = await HeaderPostsService._validate_location(mock_header_input)
        
        assert result == mock_location_succeed
    
    @pytest.mark.parametrize("isLocationEmpty, location_value, message", [
        (True, " ", "A location must be provided"),
        (False, [41.73548345343, 2.5423642846], "Site not found"),
        (False, "C/Test, 1234", "Site not found")
    ])
    @pytest.mark.asyncio
    async def test__validate_location_errors(
        self,
        mock_header_input,
        mocker: MockFixture,
        isLocationEmpty,
        location_value,
        mock_expected_output_error,
        message
    ):
        
        setattr(mock_header_input, "location", location_value)
        if isLocationEmpty:
            setattr(mock_header_input, "location", None)
            mock_expected_output_error["details"] = message
            
            
        mocker.patch("app.utils.maps_utils.fetch_geocode_data", return_value=mock_expected_output_error)
        mocker.patch("app.utils.maps_utils.fetch_reverse_geocode_data", return_value=mock_expected_output_error)

        result = await HeaderPostsService._validate_location(mock_header_input)

        assert result == mock_expected_output_error