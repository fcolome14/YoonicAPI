# import json

# import pytest
# from fastapi import HTTPException
# from pytest_mock import MockerFixture

# from app.exception_handlers import custom_http_exception_handler
# from app.routers import posts
# from app.schemas import schemas
# from app.models import EventsHeaders
# from app.schemas import NewPostHeaderInput
# from app.success_handlers import success_response
# from app.services.retrieve_service import RetrieveService
# from tests.routers.helpers import mock_data


# class TestPosts:

#     @pytest.fixture
#     def mock_request(self, mocker: MockerFixture):
#         mock_request = mocker.Mock()

#         mock_request.headers = {
#             "request-id": "default_request_id",
#             "client-type": "unknown",
#         }

#         return mock_request
    
#     @pytest.fixture
#     def mock_db_header(self):
#         mock_header = EventsHeaders(
#             id=1,
#             title="Test",
#             description="This is a test",
#             address="C/Test, 123",
#             coordinates="41.62724, 2.4848944",
#             img="https://path.com/image1",
#             img2="https://path.com/image2",
#             owner_id=1,
#             category=2,
#             created_at="1734607775.017824",
#             status=1,
#             score=0
#         )

#         return mock_header
    
#     @pytest.fixture
#     def mock_new_header_input(self):
#         mock_header = NewPostHeaderInput(
#             id=1,
#             title="Test",
#             description="This is a test",
#             location="C/Test, 123",
#             category=2,
#             status=1,
#         )

#         return mock_header

#     @pytest.mark.parametrize("found_record, message", [(False, "No pending headers"), (True, "Found pending headers")])
#     def test_new_post_succeed(self, mocker: MockerFixture, mock_request, found_record,  message, mock_db_header):
#         db_session = mocker.Mock()

#         if not found_record:
#             db_session.query().filter().first.return_value = None
#             header = None
#         else:
#             db_session.query().filter().first.return_value = mock_db_header
#             header = RetrieveService.generate_header_structure(mock_db_header)
#         expected_output = success_response(message, header, mock_request)
        
#         response = posts.new_post(db_session, 1, mock_request)
        
#         assert response == expected_output
    
#     @pytest.mark.asyncio
#     async def test_create_header_succeed(self, mocker: MockerFixture, mock_request, mock_new_header_input, mock_db_header):
#         db_session = mocker.Mock()
        
#         mock_response = {"status": "success", "message": "Approved header", "header": mock_db_header}
#         expected_output = success_response(mock_response.get("message"), mock_response.get("header"), mock_request)
#         mocker.patch(
#             "app.services.post_service.PostService.process_header",
#             return_value=mock_response,
#         )
        
#         response = await posts.create_header(mock_new_header_input, db_session, 1, mock_request)
        
#         assert response == expected_output
    
#     @pytest.mark.skipif
#     @pytest.mark.parametrize(
#         "single_rate, custom_each_day, custom_option_selected, repeat",
#         [
#             (True, False, False, False),
#             (False, False, False, True),
#             (True, False, False, True),
#             (True, False, True, True),
#             # (True, True, True, True),
#         ],
#     )
#     @pytest.mark.skipif
#     @pytest.mark.asyncio
#     async def test_create_post_succeed(
#         self,
#         mocker: MockerFixture,
#         mock_request,
#         single_rate,
#         custom_each_day,
#         custom_option_selected,
#         repeat,
#     ):

#         db_session = mocker.Mock()
#         mock_rate = mock_data.create_mock_rate(single=single_rate)
#         mock_line = mock_data.create_mock_line(
#             mock_rate, custom_each_day=custom_each_day
#         )
#         mock_input = mock_data.create_mock_input(
#             line=mock_line,
#             custom_each_day=custom_each_day,
#             custom_option_selected=custom_option_selected,
#             repeat=repeat,
#         )
#         mock_geocode_data = {
#             "status": "success",
#             "point": (float(41.147353252), float(2.27842874)),
#             "address": "C/Test, 123",
#         }

#         mocker.patch(
#             "app.routers.posts.maps_utils.fetch_geocode_data",
#             return_value=mock_geocode_data,
#         )
#         expected_output = schemas.SuccessResponse(
#             status="success",
#             message="New event created",
#             data={},
#             meta={
#                 "request_id": mock_request.headers.get("request-id"),
#                 "client": mock_request.headers.get("client-type"),
#             },
#         )

#         response = await posts.create_post(
#             posting_data=mock_input, db=db_session, request=mock_request
#         )

#         assert expected_output == response
#         if repeat:
#             db_session.add.call_count == 5
#         db_session.add.call_count == 3

#     @pytest.mark.skipif
#     @pytest.mark.parametrize(
#         "single_rate, custom_each_day, custom_option_selected, repeat, err_type, message, details, data, invalid_where_to, mock_geocode",
#         [
#             (
#                 False,
#                 True,
#                 False,
#                 False,
#                 "OSM",
#                 "Lines can't be <List>, expected single object",
#                 None,
#                 True,
#                 False,
#                 {
#                     "status": "success",
#                     "point": (float(41.147353252), float(2.27842874)),
#                     "address": "C/Test, 123",
#                 },
#             ),
#             (
#                 False,
#                 True,
#                 True,
#                 False,
#                 "OSM",
#                 "Line data must be a list in custom_each_day mode",
#                 None,
#                 True,
#                 False,
#                 {
#                     "status": "success",
#                     "point": (float(41.147353252), float(2.27842874)),
#                     "address": "C/Test, 123",
#                 },
#             ),
#             (
#                 False,
#                 False,
#                 False,
#                 True,
#                 "OSM",
#                 "Invalid 'every' value",
#                 None,
#                 False,
#                 True,
#                 {
#                     "status": "success",
#                     "point": (float(41.147353252), float(2.27842874)),
#                     "address": "C/Test, 123",
#                 },
#             ),
#             (
#                 False,
#                 False,
#                 True,
#                 True,
#                 "OSM",
#                 "Invalid 'every' value",
#                 None,
#                 False,
#                 True,
#                 {
#                     "status": "success",
#                     "point": (float(41.147353252), float(2.27842874)),
#                     "address": "C/Test, 123",
#                 },
#             ),
#             (
#                 True,
#                 False,
#                 False,
#                 True,
#                 "OSM",
#                 "Error fetching geocode data",
#                 None,
#                 False,
#                 False,
#                 {"status": "error", "details": "Error fetching geocode data"},
#             ),
#         ],
#     )
#     @pytest.mark.skipif
#     @pytest.mark.asyncio
#     async def test_create_post_exceptions(
#         self,
#         mocker: MockerFixture,
#         mock_request,
#         single_rate,
#         custom_each_day,
#         custom_option_selected,
#         repeat,
#         message,
#         details,
#         err_type,
#         mock_geocode,
#         data,
#         invalid_where_to,
#     ):

#         db_session = mocker.Mock()

#         mock_rate = mock_data.create_mock_rate(single=single_rate)
#         if data and custom_option_selected and custom_each_day:
#             mock_line = mock_data.create_mock_line(mock_rate, custom_each_day=False)
#         elif data and not custom_option_selected and custom_each_day:
#             mock_line = mock_data.create_mock_line(mock_rate, custom_each_day=True)
#         else:
#             mock_line = mock_data.create_mock_line(
#                 mock_rate, custom_each_day=custom_each_day
#             )
#         mock_input = mock_data.create_mock_input(
#             line=mock_line,
#             custom_each_day=custom_each_day,
#             custom_option_selected=custom_option_selected,
#             repeat=repeat,
#         )
#         if invalid_where_to:
#             mock_input = mock_data.create_mock_input(
#                 line=mock_line,
#                 custom_each_day=custom_each_day,
#                 custom_option_selected=custom_option_selected,
#                 repeat=repeat,
#                 where_to=25,
#             )

#         mocker.patch(
#             "app.routers.posts.maps_utils.fetch_geocode_data", return_value=mock_geocode
#         )
#         expected_error = {
#             "status": "error",
#             "message": (
#                 mock_geocode.get("details")
#                 if mock_geocode.get("status") == "error"
#                 else message
#             ),
#             "data": {
#                 "type": err_type,
#                 "message": (
#                     mock_geocode.get("details")
#                     if mock_geocode.get("status") == "error"
#                     else message
#                 ),
#                 "details": details,
#             },
#             "meta": {
#                 "request_id": mock_request.headers.get("request-id"),
#                 "client": mock_request.headers.get("client-type"),
#             },
#         }

#         with pytest.raises(HTTPException) as exception_data:
#             await posts.create_post(
#                 posting_data=mock_input, db=db_session, request=mock_request
#             )

#         error_output = custom_http_exception_handler(mock_request, exception_data.value)
#         error_body = error_output.body.decode("utf-8")
#         error_response = json.loads(error_body)

#         assert expected_error == error_response
