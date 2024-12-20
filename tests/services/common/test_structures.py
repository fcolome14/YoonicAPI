import pytest
from app.models import EventsHeaders
from app.services.common.structures import GenerateStructureService

@pytest.fixture
def mock_header_record():
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
def expected_serialized_header_record(mock_header_record):
    return {
        column.name: getattr(mock_header_record, column.name) 
            for column in mock_header_record.__table__.columns
            }

class TestGenerateStructureService:
    
    @pytest.mark.parametrize("fetched_record", [True, False])
    def test_generate_header_structure(self, mock_header_record, expected_serialized_header_record, fetched_record):
        
        if not fetched_record:
            mock_header_record = None
            
        response = GenerateStructureService.generate_header_structure(mock_header_record)
        
        if fetched_record:
            assert response == expected_serialized_header_record
        else:
            assert response == None  # noqa: E711
