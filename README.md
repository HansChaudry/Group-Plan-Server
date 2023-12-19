<div style="text-align:center">
    <h1 align="center">Group Plan</h1>
</div>

### Table of Contents

1. [Intro](#intro)
2. [Technology and Packages used](#technology-and-packages-used)
3. [Installation](#installation)
4. [Usage](#usage)

## Intro

This is the Repository for the backend client of the Group Plan application.

The backend is powered by our two different microservices, Recipes and Users. It is intended to follow REST principles where different routes can describe different objects and various methods can perform CRUD operations on our database.

It provides the frontend application the power to communicate with various groups and carry out the different needed processes to run a successful Group Planning meal.

## Technology and Packages used

<p style="font-size:16px;">
    <a href="https://www.djangoproject.com/">Django</a>
    : The framework to build our backend server
</p>
<p style="font-size:16px;">
    <a href="https://azure.microsoft.com/en-us/">Azure</a>
    : Cloud infrastructure that powers our database, file hosting, and deployments
</p>

## Installation

Travel to the directory you wish to store the Group-Plan-Server repo and run:

```bash
$ git clone https://github.com/HansChaudry/Group-Plan-Server.git
```

Navigate into the directory for the group plan server then run:

```bash
$ pip install -r requirements.txt
```

You will need to create a .env file within the base directory, the following is an example of its contents:

```
DB_NAME=Group-Plan-DB
DB_USER=SOME_DB_USER
DB_PASSWORD=SOME_PASSWORD
DB_HOST=SOME_DB_URL
DB_PORT=SOME_DB_PORT
```

## Usage

To run the server you can run:
```bash
$ python manage.py runserver
```

Since the server uses Django, you can use any commands provided by Django in their [documentation](https://docs.djangoproject.com/en/5.0/)
