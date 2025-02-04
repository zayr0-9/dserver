import React, { useState } from 'react';
import axios from 'axios'; //api library

const Terminal = () => {
  //useState creates a variable and a function that can modify that variable
  //command is a variable, setCommand function modifies it
  const [command, setCommand] = useState('');
  const [output, setOutput] = useState('');
  //isLoading is a boolean variable, setIsLoading function modifies it
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  //this function is called when user tries to run a terminal command
  const executeCommand = async () => {
    //Removes the leading and trailing white space
    //and line terminator characters from a string.
    //check if its not empty otherwise quit with error
    if (!command.trim()) {
      setError('Please enter a command.');
      return;
    }

    //set isLoading to true
    setIsLoading(true);
    //reset Error
    setError('');

    try {
      //this is how we use axios library to use POST HTTP command
      // to a specific url and also send the command variable
      const response = await axios.post('/api/terminal/', { command });
      //set Output variable, get data from repsonse object using data attribute
      //the names match what is sent from backend
      setOutput(response.data.output || response.data.error);
    } catch (err) {
      //try to catch error, ? syntax checks if variable exists
      setError(err.response?.data?.error || 'An error occured.');
    } finally {
      //set isLoading false since
      setIsLoading(false);
    }
  };
  //UI/UX part, return front end for user to view
  return (
    <div style={styles.terminal}>
      <h1>Terminal</h1>
      <div style={styles.inputContainer}>
        <input
          type="text"
          value={command}
          onChange={(e) => setCommand(e.target.value)}
          placeholder="Enter command"
          style={styles.input}
          disabled={isLoading}
        />
        <button
          onClick={executeCommand}
          style={styles.button}
          disabled={isLoading}
        >
          {isLoading ? 'Executing...' : 'Execute'}
        </button>
      </div>
      {error && <p style={styles.error}>{error}</p>}
      <pre style={styles.output}>{output}</pre>
    </div>
  );
};

const styles = {
  terminal: {
    fontFamily: 'monospace',
    backgroundColor: '#1e1e1e',
    color: '#00ff00',
    padding: '20px',
    borderRadius: '5px',
    maxWidth: '800px',
    margin: '0 auto',
  },
  inputContainer: {
    display: 'flex',
    gap: '10px',
    marginBottom: '20px',
  },
  input: {
    flex: 1,
    padding: '10px',
    backgroundColor: '#2d2d2d',
    border: 'none',
    color: '#00ff00',
    borderRadius: '5px',
  },
  button: {
    padding: '10px 20px',
    backgroundColor: '#007bff',
    border: 'none',
    color: '#fff',
    borderRadius: '5px',
    cursor: 'pointer',
  },
  error: {
    color: '#ff0000',
  },
  output: {
    backgroundColor: '#2d2d2d',
    padding: '10px',
    borderRadius: '5px',
    height: '300px',
    overflowY: 'auto',
  },
};

export default Terminal;
