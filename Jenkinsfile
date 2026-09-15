pipeline {
    agent any
    environment {
        // Homebrew services start with a minimal launchd PATH on macOS.
        // Keep the additions harmless on Linux agents and preserve their PATH.
        PATH = "/opt/homebrew/bin:/Users/dora/.local/bin:/Users/dora/.npm-global/bin:${env.PATH}"
    }
    options {
        timestamps()
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '20'))
    }
    parameters {
        choice(name: 'TARGET_PROFILE', choices: ['asteria-contract', 'workbench-contract'], description: 'Asteria is the primary SUT; workbench-contract validates the control plane.')
        string(name: 'ASTERIA_PROJECT_ROOT', defaultValue: '', description: 'Absolute Asteria checkout path on the Jenkins agent; required for asteria-contract.')
        string(name: 'ASTERIA_PYTHON', defaultValue: 'python3', description: 'Python runtime with Asteria dependencies.')
        string(name: 'TARGET_HOST', defaultValue: 'host.docker.internal', description: 'Read-only target host for Postman/JMeter.')
        string(name: 'TARGET_PORT', defaultValue: '8018', description: 'Read-only target port for Postman/JMeter.')
        booleanParam(name: 'RUN_NEWMAN', defaultValue: false, description: 'Run the registered read-only Postman collection.')
        booleanParam(name: 'RUN_JMETER', defaultValue: false, description: 'Run the registered read-only JMeter plan; use only in an isolated environment.')
    }
    stages {
        stage('Prepare') {
            steps {
                sh 'python3 -m venv .ci-venv'
                sh '.ci-venv/bin/pip install -r backend/requirements.txt'
            }
        }
        stage('Tool preflight') {
            steps {
                sh 'python3 --version && git --version && newman --version && jmeter --version'
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
        stage('Postman read-only smoke') {
            when {
                expression { params.RUN_NEWMAN }
            }
            steps {
                sh '''
                    mkdir -p artifacts
                    newman run collections/asteria-agent-smoke.postman_collection.json \
                        --env-var "base_url=http://${TARGET_HOST}:${TARGET_PORT}" \
                        --reporters cli,junit \
                        --reporter-junit-export artifacts/newman.xml
                '''
            }
        }
        stage('JMeter read-only performance') {
            when {
                expression { params.RUN_JMETER }
            }
            steps {
                sh '''
                    mkdir -p artifacts/jmeter-report
                    jmeter -n -t performance/asteria-readonly.jmx \
                        -JbaseUrl="${TARGET_HOST}" \
                        -Jport="${TARGET_PORT}" \
                        -Jthreads=1 -JrampSeconds=1 \
                        -l artifacts/jmeter-results.jtl \
                        -e -o artifacts/jmeter-report
                '''
            }
        }
    }
    post {
        always {
            archiveArtifacts artifacts: 'artifacts/**/*', allowEmptyArchive: true, fingerprint: true
            junit testResults: 'artifacts/**/*.xml', allowEmptyResults: true
            sh 'rm -rf .ci-venv'
        }
    }
}
