from setuptools import setup, find_packages

if __name__ == '__main__':
    setup(
        name='aiosyncqueue',
        version='1.0.0',
        author='Aaron Tsang',
        author_email='tsangwpx@gmail.com',
        description='SyncQueue for asyncio',
        packages=find_packages(include=['aiosyncqueue']),
        classifiers=[
            "Programming Language :: Python :: 3",
            "License :: OSI Approved :: MIT License",
            "Operating System :: OS Independent",
        ],
        python_requires='>=3.6',
    )
