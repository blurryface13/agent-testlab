pipeline {
    agent any
    options {
        timestamps()
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '20'))
    }
    parameters {
        choice(name: 'TARGET_PROFILE', choices: ['asteria-contract', 'workbench-contract'], description: 'Asteria is the primary SUT; workbench-contract validates the control plane.')
        string(name: 'ASTERIA_PROJECT_ROOT', defaultValue: '', description: 'Absolute Asteria checkout path on the Jenkins agent; required for asteria-contract.')
        string(name: 'ASTERIA_PYTHON', defaultValue: 'python3', description: 'Python runtime with Asteria dependencies.')
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
                sh '''
                    mkdir -p artifacts
                    if [ "$TARGET_PROFILE" = "asteria-contract" ]; then
                        test -n "$ASTERIA_PROJECT_ROOT"
                        PYTHONPATH="$ASTERIA_PROJECT_ROOT" "$ASTERIA_PYTHON" -m pytest "$ASTERIA_PROJECT_ROOT/tests/test_testlab_contract.py" -q --junitxml=artifacts/asteria-junit.xml
                    else
                        PYTHONPATH=backend .ci-venv/bin/python -m pytest backend/tests/test_testing_workbench.py -q --junitxml=artifacts/workbench-junit.xml
                    fi
                '''
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
