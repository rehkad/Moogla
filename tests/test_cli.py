from typer.testing import CliRunner
from moogla.cli import app

runner = CliRunner()

def test_help():
    result = runner.invoke(app, ['--help'])
    assert result.exit_code == 0
    assert 'serve' in result.output
    assert 'pull' in result.output

def test_pull():
    result = runner.invoke(app, ['pull', 'test-model'])
    assert result.exit_code == 0
    assert 'Pulling test-model ... done.' in result.output
