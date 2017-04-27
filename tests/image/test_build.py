# -*- coding: utf-8 -*-
import os

import mock
import pytest
from click.testing import CliRunner

from shub import exceptions as shub_exceptions
from shub.image.build import cli
from ..utils import format_expected_progress


@pytest.fixture
def test_mock():
    """Mock for shub image test command"""
    with mock.patch('shub.image.build.test_cmd') as m:
        yield m


@pytest.fixture
def wizard_mock():
    """Mock for shub.utils.create_scrapinghub_yml_wizard"""
    with mock.patch('shub.utils.create_scrapinghub_yml_wizard') as m,\
            mock.patch('shub.utils.has_project_access', return_value=True):
        yield m


def test_cli(docker_client_mock, project_dir, test_mock):
    docker_client_mock.build.return_value = [
        {"stream": "all is ok"},
        {"stream": "Successfully built 12345"}
    ]
    runner = CliRunner()
    result = runner.invoke(cli, ["dev", "-v"])
    assert result.exit_code == 0
    docker_client_mock.build.assert_called_with(
        decode=True, path=project_dir, tag='registry/user/project:1.0')
    test_mock.assert_called_with("dev", None)


def test_cli_with_progress(docker_client_mock, project_dir, test_mock):
    docker_client_mock.build.return_value = [
        {"stream": "Step 1/3 : FROM some_image"},
        {"stream": "some internal actions"},
        {"stream": "Step 2/3 : RUN cmd1"},
        {"stream": "some other actions"},
        {"stream": "Step 3/3 : RUN cmd2"},
        {"stream": "Successfully built 12345"}
    ]
    runner = CliRunner()
    result = runner.invoke(cli, ["dev"])
    assert result.exit_code == 0
    expected = format_expected_progress(
        'Building registry/user/project:1.0.\n\r'
        'Steps:   0%|          | 0/1\r'
        'Steps: 100%|██████████| 3/3\n'
        'The image registry/user/project:1.0 build is completed.\n'
    )
    assert expected in result.output


def test_cli_custom_version(docker_client_mock, project_dir, test_mock):
    docker_client_mock.build.return_value = [
        {"stream": "all is ok"},
        {"stream": "Successfully built 12345"}
    ]
    runner = CliRunner()
    result = runner.invoke(cli, ["dev", "--version", "test"])
    assert result.exit_code == 0
    docker_client_mock.build.assert_called_with(
        decode=True, path=project_dir, tag='registry/user/project:test')
    test_mock.assert_called_with("dev", "test")


def test_cli_no_dockerfile(docker_client_mock, project_dir):
    docker_client_mock.build.return_value = [
        {"error": "Minor", "errorDetail": "Testing output"},
        {"stream": "Successfully built 12345"}
    ]
    os.remove(os.path.join(project_dir, 'Dockerfile'))
    runner = CliRunner()
    result = runner.invoke(cli, ["dev"])
    assert result.exit_code == shub_exceptions.NotFoundException.exit_code


@pytest.mark.usefixtures('project_dir')
def test_cli_fail(docker_client_mock):
    docker_client_mock.build.return_value = [
        {"error": "Minor", "errorDetail": "Test"}
    ]
    runner = CliRunner()
    result = runner.invoke(cli, ["dev"])
    assert result.exit_code == shub_exceptions.RemoteErrorException.exit_code


@pytest.mark.parametrize('skip_tests_flag', ['-S', '--skip-tests'])
def test_cli_skip_tests(docker_client_mock, test_mock, project_dir, skip_tests_flag):
    docker_client_mock.build.return_value = [
        {"stream": "all is ok"},
        {"stream": "Successfully built 12345"}
    ]
    runner = CliRunner()
    result = runner.invoke(cli, ["dev", skip_tests_flag])
    assert result.exit_code == 0
    docker_client_mock.build.assert_called_with(
        decode=True, path=project_dir, tag='registry/user/project:1.0')
    assert test_mock.call_count == 0


@pytest.mark.usefixtures('wizard_mock')
@pytest.mark.usefixtures('test_mock')
def test_cli_calls_onboarding_wizard(docker_client_mock, project_dir):
    with open(os.path.join(project_dir, 'scrapinghub.yml'), 'w') as f:
        f.write('apikey: abcdef')
    docker_client_mock.build.return_value = [
        {"stream": "all is ok"},
        {"stream": "Successfully built 12345"}
    ]
    runner = CliRunner()
    result = runner.invoke(cli, ['12345'])
    assert result.exit_code == shub_exceptions.NotFoundException.exit_code
    result = runner.invoke(cli, input='12345\nmyregistry/X/Y\n')
    assert result.exit_code == 0
    docker_client_mock.build.assert_called_with(
        decode=True, path=project_dir, tag='myregistry/X/Y:1.0')
