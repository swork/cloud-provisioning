from setuptools import setup
import os

# see __init__.py for note about environ context
import logging
logging.basicConfig(datefmt='', level=os.environ.get('LEVEL', 'DEBUG'))
logger = logging.getLogger(__name__)

install_only_runtime = os.environ.get('INSTALL_ONLY_RUNTIME')

packages = []
install_requires = []

if install_only_runtime:
    if install_only_runtime == 'renlabs.runtime.aws.wsgi':
        packages = [install_only_runtime]
        logger.info('Installing only the AWS runtime')
    else:
        raise RuntimeError("INSTALL_ONLY_RUNTIME unknown package: ",
                           install_only_runtime)
else:
    packages = [
        'renlabs.provisioning.aws',
        'renlabs.runtime.aws.wsgi' ]
    install_requires = ['boto3']
    logger.info('Installing provisioning code; including all runtimes')

setup(
    name='cloud-provisioning',
    version='1.0.0rc0',
    description='Capture what I once knew about programmatic cloud-service setup',
    author='Steve Work',
    author_email='steve@work.renlabs.com',
    packages=packages,
    install_requires=install_requires
)
