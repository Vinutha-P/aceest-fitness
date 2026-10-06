// Jenkins pipeline for the ACEest Fitness & Gym BUILD & Quality Gate stage.
//
// This acts as the secondary validation layer: it pulls the latest code
// from GitHub and performs a clean build of the environment.
//
// Required Jenkins plugins:
//   - Git            (source checkout)
//   - Pipeline
//   - Docker Pipeline (docker, dockerFile, dockerCompose)
//   - Credentials Binding

pipeline {
    agent any

    environment {
        APP_NAME        = 'aceest-fitness'
        IMAGE_TAG       = "${BUILD_NUMBER}"
        PYTHON_VERSION  = '3.12'
        // Credentials id must match a Jenkins "Username with password" entry
        // or use 'ssh-agent' for an SSH deploy key.
        GIT_CREDENTIALS = 'github-credentials'
    }

    options {
        timestamps()
        buildDiscarder(logRotator(numToKeepStr: '10'))
        timeout(time: 30, unit: 'MINUTES')
        disableConcurrentBuilds()
    }

    stages {

        stage('Checkout') {
            steps {
                echo "Checking out ${GIT_BRANCH} (build #${BUILD_NUMBER})"
                checkout scm
                sh 'git log --oneline -5'
            }
        }

        stage('Build Environment') {
            steps {
                echo 'Creating a clean virtual environment and installing dependencies'
                sh '''
                    python3 --version
                    python3 -m venv .venv || python3 -m virtualenv .venv
                    . .venv/bin/activate
                    pip install --upgrade pip
                    pip install -r requirements.txt
                '''
            }
        }

        stage('Lint') {
            steps {
                echo 'Running flake8 static analysis'
                sh '''
                    . .venv/bin/activate
                    flake8 . --count --statistics
                '''
            }
        }

        stage('Unit Tests') {
            steps {
                echo 'Executing the pytest suite'
                sh '''
                    . .venv/bin/activate
                    python -m pytest -v --cov=aceest --cov-report=term
                '''
            }
        }

        stage('Docker Build') {
            steps {
                echo "Building Docker image ${APP_NAME}:${IMAGE_TAG}"
                sh """
                    docker build -t ${APP_NAME}:${IMAGE_TAG} .
                    docker images ${APP_NAME}:${IMAGE_TAG}
                """
            }
        }

        stage('Container Verification') {
            steps {
                echo 'Running the test suite inside the container'
                sh """
                    docker run --rm \
                        -v \$(pwd)/tests:/app/tests:ro \
                        ${APP_NAME}:${IMAGE_TAG} \
                        sh -c "pip install --no-cache-dir pytest pytest-cov >/dev/null 2>&1 && python -m pytest -q /app/tests"
                """
            }
        }
    }

    post {
        success {
            echo "BUILD SUCCESSFUL: ${JOB_NAME} #${BUILD_NUMBER}"
        }
        failure {
            echo "BUILD FAILED: ${JOB_NAME} #${BUILD_NUMBER}"
            // Archive the Python traceback / pytest output for debugging.
            sh 'docker ps -a || true'
        }
        always {
            cleanWs()
        }
    }
}