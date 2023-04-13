from setuptools import setup

setup(
    name = "demo_collab",
    version='1.0',
    py_modules=['template_generator'],
    install_requires = [
        'Click'
    ],
    entry_points = '''
        [console_scripts]
        template_generator=template_generator:demo_collab
    '''
)