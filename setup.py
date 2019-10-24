from setuptools import find_packages, setup


with open('README.md', 'rb') as f:
    LONG_DESCRIPTION = f.read().decode('utf-8')


setup(
    name="airflow-queue-stats",
    version="0.1.4",
    description='An airflow plugin for viewing queue statistics.',
    long_description=LONG_DESCRIPTION,
    long_description_content_type='text/markdown',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    keywords='airflow airflow-docker celery flower worker queue plugin',
    url='https://github.com/airflowdocker/airflow-queue-stats',
    license='MIT',
    author='Hunter Senft-Grupp',
    author_email='huntcsg@gmail.com',
    package_dir={
        "": "src"
    },
    packages=find_packages("src"),
    python_requires='>=2.7,!=3.0.*,!=3.1.*,!=3.2.*,!=3.3.*,!=3.4.*',
    install_requires=[
        'apache-airflow[celery]',
    ],
    extras_require={
        'testing': [
            'pytest',
            'pytest-cov',
        ],
        'linting': [
            'isort',
            'black',
        ]
    },
    entry_points={
        "airflow.plugins": [
            "queue_stats = airflow_queue_stats.plugin:QueueStatsPlugin"
        ]
    },
)
