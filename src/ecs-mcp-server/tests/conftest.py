"""
Pytest configuration for ECS MCP Server tests.
"""

import os
import tempfile
from typing import Generator

import pytest


@pytest.fixture
def temp_dir() -> Generator[str, None, None]:
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield tmp_dir


@pytest.fixture
def flask_app_dir(temp_dir: str) -> str:
    """Create a sample Flask application directory."""
    app_dir = os.path.join(temp_dir, "flask-app")
    os.makedirs(app_dir)

    # Create app.py
    with open(os.path.join(app_dir, "app.py"), "w") as f:
        f.write(
            """
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/')
def hello():
    return "Hello, World!"

@app.route('/health')
def health():
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
"""
        )

    # Create requirements.txt
    with open(os.path.join(app_dir, "requirements.txt"), "w") as f:
        f.write("flask==2.0.1\nWerkzeug==2.0.1\n")

    # Create .env file
    with open(os.path.join(app_dir, ".env"), "w") as f:
        f.write("FLASK_ENV=development\nDEBUG=true\n")

    return app_dir


@pytest.fixture
def express_app_dir(temp_dir: str) -> str:
    """Create a sample Express.js application directory."""
    app_dir = os.path.join(temp_dir, "express-app")
    os.makedirs(app_dir)

    # Create app.js
    with open(os.path.join(app_dir, "app.js"), "w") as f:
        f.write(
            """
const express = require('express');
const app = express();
const port = process.env.PORT || 3000;

app.get('/', (req, res) => {
  res.send('Hello, World!');
});

app.get('/health', (req, res) => {
  res.json({ status: 'healthy' });
});

app.listen(port, () => {
  console.log(`Server listening at http://localhost:${port}`);
});
"""
        )

    # Create package.json
    with open(os.path.join(app_dir, "package.json"), "w") as f:
        f.write(
            """
{
  "name": "express-app",
  "version": "1.0.0",
  "description": "Sample Express.js application",
  "main": "app.js",
  "scripts": {
    "start": "node app.js",
    "test": "echo \\"Error: no test specified\\" && exit 1"
  },
  "dependencies": {
    "express": "^4.17.1"
  }
}
"""
        )

    # Create .env file
    with open(os.path.join(app_dir, ".env"), "w") as f:
        f.write("NODE_ENV=development\nPORT=3000\n")

    return app_dir


@pytest.fixture
def react_app_dir(temp_dir: str) -> str:
    """Create a sample React application directory."""
    app_dir = os.path.join(temp_dir, "react-app")
    os.makedirs(os.path.join(app_dir, "src"))

    # Create package.json
    with open(os.path.join(app_dir, "package.json"), "w") as f:
        f.write(
            """
{
  "name": "react-app",
  "version": "0.1.0",
  "private": true,
  "dependencies": {
    "react": "^17.0.2",
    "react-dom": "^17.0.2",
    "react-scripts": "5.0.0"
  },
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build",
    "test": "react-scripts test",
    "eject": "react-scripts eject"
  }
}
"""
        )

    # Create App.jsx
    with open(os.path.join(app_dir, "src", "App.jsx"), "w") as f:
        f.write(
            """
import React from 'react';

function App() {
  return (
    <div className="App">
      <header className="App-header">
        <h1>Hello, World!</h1>
      </header>
    </div>
  );
}

export default App;
"""
        )

    # Create .env file
    with open(os.path.join(app_dir, ".env"), "w") as f:
        f.write("REACT_APP_API_URL=http://localhost:3000/api\n")

    return app_dir
