YoonicAPI Documentation
========================

Welcome to the YoonicAPI documentation. This API provides endpoints to manage users and related functionalities, offering features like user creation, authentication, and data retrieval.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   introduction
   installation
   usage
   api_reference
   contributing
   changelog

API Reference
-------------
Below is the auto-generated API reference for the project. It lists all modules, classes, and functions with their docstrings.

.. automodule:: app
   :members:
   :undoc-members:
   :show-inheritance:

   app 
   database
   routers
   schemas

Introduction
============

YoonicAPI is a RESTful web service built using FastAPI. It leverages PostgreSQL for data persistence and supports modern development practices such as automated deployment and testing.

Features:
- User management (create, retrieve, update, delete)
- JWT-based authentication
- Modular and scalable architecture

Installation
============

Instructions for setting up the YoonicAPI locally or on a production server are available in the :doc:`installation` section.

.. code-block:: bash

   pip install -r requirements.txt

Usage
=====

Learn how to interact with the API endpoints using HTTP clients like Postman or cURL in the :doc:`usage` guide.

.. code-block:: bash

   uvicorn app.main:app --reload

API Reference
=============

Comprehensive documentation for all API endpoints can be found in the :doc:`api_reference` section. Each endpoint includes:
- HTTP methods and routes
- Input parameters and response models
- Examples and error codes

Contributing
============

If you'd like to contribute to YoonicAPI, refer to the :doc:`contributing` guidelines for setting up a development environment, coding standards, and pull request processes.

Changelog
=========

Track the history of changes, updates, and bug fixes in the :doc:`changelog`.

---

Add the detailed content for each of these sections in separate `.rst` files (e.g., `introduction.rst`, `api_reference.rst`) and link them in your table of contents. This layout provides a user-friendly structure for both developers and end-users.
