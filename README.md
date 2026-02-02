# Online-Cinema-API
Api service for cinema management written on Fast Api
# Installing using GitHub and run with Docker
Execute these commands. Docker should be installed

```
git clone https://github.com/Olexii-Babii/Online-Cinema-API.git
cd Online-Cinema-API
mv .env.sample .env
docker compose up --build
```
# Run tests with docker
```
docker compose -f docker-compose-tests.yaml up --build
```
# Getting access
if you want to test Api you should use Swagger.
```
username: admin
password: Password12345@
```

You can use already created admin user for login:
```
email: admin@example.com
password: Password12347@
```
Or you can create your own user (just user)
- create user via accounts/register/
- activate account via accounts/activate/ (you should get activation token from mailhog email(not link))
- get access token via accounts/login/

User Groups:
- User: Access to the basic user interface.
- Moderator: In addition user interface access, can manage movies, genres, stars.
- Admin: Inherits all permissions from the above roles and can manage users profiles.


# Features
- JWT authenticated
- Setting dependencies with poetry 
- Documentation is located at /docs/ (with auth)
- Managing films
- Creating movies, genres, stars (for moder/admin)
- Creating profile for users with uploading avatars(minio)
- Creating users favorite list with filtering and sorting
- Sending emails for users during process of registration(mailhog)
- Creating delay tasks for deleting expired activation tokens(celery)
- Tracking tasks(flower)
- Pgadmin for managing database
- Alembic for making migrations
- Filtering all movie with different parameters(genres, directors, year, price and other)

# Apps

- Main Fast Api app: http://127.0.0.1:8000/
- Pgadmin: http://127.0.0.1:3333/
- Mailhog: http://127.0.0.1:8025/
- Minio: http://127.0.0.1:9000/
- Flower: http://127.0.0.1:5555/
