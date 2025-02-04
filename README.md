[![MIT License](https://img.shields.io/github/license/fcolome14/yoonicapi.svg)](https://github.com/fcolome14/YoonicAPI?tab=MIT-1-ov-file)
[![Linnkedin](	https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/fcolome/)

# YoonicAPI

YoonicAPI is a FastAPI-based application that integrates with a PostgreSQL database, designed to host requests from Yoonic mobile app. Follow the instructions below to set up your local environment and contribute to the project.

## Steps to run this project:

> **_NOTE:_**   Before starting, you must ensure you have downloaded PostgreSQL database as well as a user configuration. In the installation wizard screen, select PostGis system extenstion

> Follow this [link](https://minikube.sigs.k8s.io/docs/start/) to install K8 and kubectl [link](https://kubernetes.io/docs/tasks/tools/install-kubectl-linux/)

### 1. Clone the Repository
First, clone the repository to your local machine:

```bash
git clone https://github.com/fcolome14/YoonicAPI.git
```

### 2. Create a Virtual Environment
Create a virtual environment to manage all necessary dependencies:
```bash
python -m venv .venv
```
### 3. Activate the Virtual Environment
Activate the virtual environment by running:

For Windows:
```bash
.\.venv\Scripts\activate
```
For MacOS/Linux:
```bash
source .venv/bin/activate
```

### 4. Install the Dependencies
Install the required dependencies listed in the requirements.txt file:
```bash
pip install -r requirements.txt
```
### 5. Add Configuration Files
Make sure you add the following configuration files to the root directory:

- .env: Add environment-specific variables such as database connection strings, API keys, etc.

    ```env
        # Database Configuration
        DATABASE_HOSTNAME=localhost
        DATABASE_PORT=5432
        DATABASE_PASSWORD=<your_password>
        DATABASE_NAME=yoonic
        DATABASE_USERNAME=<your_username>
        
        # Security Settings
        SECRET_KEY=<your_secret_key>
        REFRESH_SECRET_KEY=<your_refresh_secret_key>
        ALGORITHM=HS256
        ACCESS_TOKEN_EXPIRE_MINUTES=30
        
        # Email Settings
        EMAIL=<your_email>
        EMAIL_PASSWORD=<your_google_app_password>
        SMTP_SERVER=smtp.gmail.com
        SMTP_PORT=587
        DOMAIN=http://localhost:8000
        EMAIL_CODE_EXPIRE_MINUTES=15
        
        # Firebase Credentials File (Path to service account JSON)
        GOOGLE_APPLICATION_CREDENTIALS=./service-account.json
        
        #NUMINATIM GEOCODING API
        NOMINATIM_BASE_URL = https://nominatim.openstreetmap.org
        USER_AGENT = <your_user_agent_name>
    ```

- account-credentials.json: This file contains sensitive account credentials that are required to run the application. Ensure this is kept secure and not committed to version control (Optional)

> **_NOTE:_**  You must get an app password to ensure the API can access the provided email:
[Google App Password](https://myaccount.google.com/apppasswords?rapt=AEjHL4NRAm5Hk99vE2WaFuM0K9kQpkbczwBR_W86n_u7-Emguk982gbEOerYl2rWj4SId6uR4U4R9zeqC-mV5CQdKpRStDty1RB9u8drKuy1qDPKr-0xAII)

## Run:
At this point you can run the app by typing:
```bash
uvicorn app.main:app --reload
```
To display the Swagger UI documentation, type into your browser: localhost:8000/docs

## Tests:
In order to run tests in the API use the command:
```bash
pytest -vv
```

## Instructions:
### 1. Create a post
When creating a new post you must consider the following flags setup:

|  	| **Simple** 	| **Simple Rep.(*)** 	| **Custom** 	| **Custom Rep.(*)** 	| **Custom Each Day** 	| **Custom Each Day Rep.(*)** 	|
|---	|---	|---	|---	|---	|---	|---	|
| **repeat** 	| False 	| True 	| False 	| True 	| False 	| True 	|
| **custom_option_selected** 	| False 	| False 	| True 	| True 	| True 	| True 	|
| **custom_each_day** 	| False 	| False 	| False 	| False 	| True 	| True 	|
| **line (type)** 	| Line	| Line	| Line 	| Line 	| List[Line] 	| List[Line] 	|

(*) Only for repeated posts, the frequency and period can be defined tunning the number of "occurrences" and:

| Repeat every ("when_to")           | 0    | 1    | 2     | 3      | 4      |
|------------------------------------|------|------|-------|--------|--------|
| custom_option_selected: False      | Day  | Week | Month | Weekday| Weekend|
| custom_option_selected: True       | Week | Month| Year  | -      | -      |

Only when using custom mode with "custom_each_day" flag set to False:

|  	| Monday 	| Tuesday 	| Wednesday 	| Thursday 	| Friday 	| Saturday 	| Sunday 	|
|---	|---	|---	|---	|---	|---	|---	|---	|
| for_days 	| 0 	| 1 	| 2 	| 3 	| 4 	| 5 	| 6 	|

This will follow the defined pattern based on a given date. If the reference date is before a day in the pattern automatically will assign a day for the next week.

Finally, every line can contain single or multiple rates, where a single rate must be indicated by a simple object while multiple must be within a list of objects

### 2. Update a post
When updating a post it's important to notice that the system will only allow the update of one header at a time. In contrast of lines and rates, the system is capable of modifying multiple records.