import pytest
from pytest_mock import MockerFixture
from app.database.connection import get_db

@pytest.fixture(autouse = True)
def db_mocking(mocker: MockerFixture):
    # mock_connection = mocker.Mock()
    # mock_cursor = mocker.Mock()
    
    # mocker.patch.object(get_db, 'get_connection', return_value = mock_connection)
    # mock_connection.cursor.return_value = mock_cursor
    
    # return mock_cursor, mock_connection
    pass