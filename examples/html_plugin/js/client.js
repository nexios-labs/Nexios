// RPC Client for browsers
// Define in a self-executing function to avoid global namespace pollution
(function (global) {
  // RPC Client Error class
  class RpcClientError extends Error {
    constructor(code, message, data = null) {
      super(message);
      this.name = "RpcClientError";
      this.code = code;
      this.data = data;
    }
  }

  class RpcClient {
    /**
     * A client for the RPC server that uses only native JavaScript features.
     * @param {string} baseUrl - The base URL of the RPC server, including the path prefix
     * (e.g., "http://localhost:8000/rpc")
     */
    constructor(baseUrl) {
      this.baseUrl = baseUrl;
      this.requestId = 0;
    }

    /**
     * Generate a unique request ID.
     * @returns {number} A unique request ID
     * @private
     */
    _generateRequestId() {
      this.requestId += 1;
      return this.requestId;
    }

    /**
     * Make an RPC request to the server.
     * @param {string} method - The name of the RPC method to call
     * @param {Object|Array} params - The parameters to pass to the method
     * @returns {Promise<any>} A promise that resolves to the response from the server
     * @private
     */
    async _makeRequest(method, params) {
      // Create the request payload
      const requestId = this._generateRequestId();
      const payload = {
        jsonrpc: "2.0",
        method: method,
        params: params,
        id: requestId,
      };

      try {
        // Send the request
        const response = await fetch(this.baseUrl, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
          },
          body: JSON.stringify(payload),
        });

        // Parse the response
        const responseData = await response.json();

        // Check if there's an error in the response
        if (responseData.error) {
          const error = responseData.error;
          throw new RpcClientError(
            error.code || -32603,
            error.message || "Unknown error",
            error.data
          );
        }

        // Return the result
        return responseData.result;
      } catch (error) {
        console.error(JSON.stringify(error));
        // Handle fetch or JSON parsing errors
        if (error instanceof RpcClientError) {
          throw error;
        }

        // Handle Response objects differently in browsers
        if (typeof Response !== "undefined" && error instanceof Response) {
          try {
            const errorData = await error.json();
            if (errorData.error) {
              throw new RpcClientError(
                errorData.error.code || -32603,
                errorData.error.message || "Server error",
                errorData.error.data
              );
            }
          } catch (jsonError) {
            // If we can't parse the error response as JSON
            throw new RpcClientError(
              -32603,
              `HTTP error: ${error.status} ${error.statusText}`,
              null
            );
          }
        }

        // Generic error
        throw new RpcClientError(
          -32603,
          `Request error: ${error.message}`,
          null
        );
      }
    }

    /**
     * Call an RPC method.
     * @param {string} method - The name of the RPC method to call
     * @param {Object|Array} params - The parameters to pass to the method
     * @returns {Promise<any>} A promise that resolves to the result of the RPC method call
     */
    async call(method, params = {}) {
      return await this._makeRequest(method, params);
    }
  }

  // Add method proxy handler to enable client.methodName() syntax
  const handler = {
    get(target, prop) {
      if (prop in target || typeof prop === "symbol" || prop === "then") {
        return target[prop];
      }

      return async (...args) => {
        // Handle both positional and named parameters
        const params =
          args.length === 1 &&
          typeof args[0] === "object" &&
          !Array.isArray(args[0])
            ? args[0] // Named parameters as object
            : args; // Positional parameters as array

        return await target._makeRequest(prop, params);
      };
    },
  };

  // Factory function to create proxied RpcClient instances
  function createRpcClient(baseUrl) {
    const client = new RpcClient(baseUrl);
    return new Proxy(client, handler);
  }

  // Expose to global scope for browsers (window)
  global.RpcClientError = RpcClientError;
  global.RpcClient = RpcClient;
  global.createRpcClient = createRpcClient;

  // Also support CommonJS and AMD
  if (typeof module !== "undefined" && module.exports) {
    module.exports = {
      RpcClientError,
      RpcClient,
      createRpcClient,
    };
  } else if (typeof define === "function" && define.amd) {
    define([], function () {
      return {
        RpcClientError,
        RpcClient,
        createRpcClient,
      };
    });
  }
})(typeof window !== "undefined" ? window : this);
