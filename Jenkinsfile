pipeline {
    agent any
    options {
        timestamps()
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '20'))
    }
    parameters {
        choice(name: 'TARGET_PROFILE', choices: ['local-mock'], description: 'Only registered local profile is enabled by default.')
        choice(name: 'SUITE', choices: ['workbench-contract'], description: 'Registered non-live suite.')
    }
    stages {
        stage('Prepare') {
            steps {
                sh 'python3 -m venv .ci-venv'
                sh '.ci-venv/bin/pip install -r backend/requirements.txt'
            }
        }
        stage('Contract tests') {
            steps {
                sh 'PYTHONPATH=backend .ci-venv/bin/python -m pytest backend/tests/test_testing_workbench.py -q --junitxml=artifacts/junit.xml'
            }
        }
    }
    post {
        always {
            archiveArtifacts artifacts: 'artifacts/**/*.xml', allowEmptyArchive: true
            junit testResults: 'artifacts/**/*.xml', allowEmptyResults: true
            sh 'rm -rf .ci-venv'
        }
    }
}
