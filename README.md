# Bryaz7 - Backend Services

## System Design

The backend service system design and database structure are available [here](https://drive.google.com/file/d/1woDyHL-idzYrLaOnmr5dbsQQTtM6nUPy/view?usp=sharing).

## Running Locally

To run locally, first set up the `.env` file. You can request the contents from the repository owner or initialize the required fields.

Then, start the Flask application using:

```commandline
export FLASK_APP=main.py
flask run
```

or

```commandline
python main.py
```

## Deployment with Docker

### Steps

**To deploy using Docker Compose:**

```commandline
docker-compose up --build -d
```

- The `-d` flag runs the container in the background.
- Configurations are defined in `docker-compose.yml` and `Dockerfile`.

**To push the container to AWS ECR:** Log in to the AWS Console with account ID `[account_ID]` and then execute these commands:

### For Development Environment

```commandline
aws ecr get-login-password --region ap-southeast-1 | docker login --username AWS --password-stdin [account_ID].dkr.ecr.ap-southeast-1.amazonaws.com
docker build -t bryaz7-backend .
docker tag bryaz7-backend:latest [account_ID].dkr.ecr.ap-southeast-1.amazonaws.com/bryaz7-backend:latest
docker push [account_ID].dkr.ecr.ap-southeast-1.amazonaws.com/bryaz7-backend:latest
aws ecs update-service --cluster bryaz7-dev-cluster --service bryaz7-backend-dev-service --force-new-deployment
```

### For Production Environment

```commandline
aws ecr get-login-password --region ap-southeast-1 | docker login --username AWS --password-stdin [account_ID].dkr.ecr.ap-southeast-1.amazonaws.com
docker build -t domain-backend .
docker tag domain-backend:latest [account_ID].dkr.ecr.ap-southeast-1.amazonaws.com/domain-backend:latest
docker push [account_ID].dkr.ecr.ap-southeast-1.amazonaws.com/domain-backend:latest
aws ecs update-service --cluster domain-prod-cluster --service domain-prod-service --force-new-deployment
```

**Troubleshooting:** If the last step keeps retrying to push the image, you might lack permissions to push to the private repository. To resolve this, configure your credentials using `aws configure`.

## Updates on Coding Conventions

**Oct 25:** Support functions have been moved from `models` to `service`.

Previously, support functions were included within the model class:

```python
# db/models/user.py

class User(BaseTable):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    ## ...Some more attributes...

    @staticmethod
    def get_user_level(user_id):
        parent = db.session.get(User, user_id)
        return parent.to_dict(subset=["id", "level"])

    ## ..Some more static methods..
```

To reduce dependencies, these support functions have been moved to the `services` class:

```python
# db/models/user.py
class User(BaseTable):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    ## ...Some more attributes...


# db/services/user.py
class UserService:
    @staticmethod
    def get_user_level(user_id):
        parent = db.session.get(User, user_id)
        return parent.to_dict(subset=["id", "level"])
    ## ..Some more static methods..
```


**Oct 16:** Instead of returning a payload with a status code in the controller when using try-except blocks:

```python
user = db.session.get(User, user_id)
if not user:
    return jsonify({"message": "User not found"}), 404
```

You should raise an `ItemNotFoundError` exception instead:

```python
user = db.session.get(User, user_id)
if not user:
    raise ItemNotFoundError("User not found")
```

The list of exception types is defined in `utils/exceptions.py`, and the list of handled exceptions in Flask can be found in `utils/error_handler.py`.