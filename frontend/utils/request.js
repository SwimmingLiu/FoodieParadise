/**
 * Custom request utility for WeChat Mini Program to support Chunked Transfer Encoding
 * Simulates SSE (Server-Sent Events) behavior
 */

export const streamRequest = ({ url, method = 'GET', data = {}, header = {}, onChunk, onComplete, onError }) => {
  const requestTask = wx.request({
    url,
    method,
    data,
    header: {
      ...header,
      'content-type': 'application/json'
    },
    enableChunked: true, // Enable chunked transfer
    success: (res) => {
      // This callback is triggered when the request is complete (but for chunked, we rely on onChunkReceived)
      if (onComplete) onComplete(res);
    },
    fail: (err) => {
      if (onError) onError(err);
    }
  });

  // Listen for chunks
  requestTask.onChunkReceived((response) => {
    if (response.data) {
      // response.data is ArrayBuffer
      const uint8Array = new Uint8Array(response.data);
      // We need a TextDecoder to decode the ArrayBuffer. 
      // Note: TextDecoder might not be available in all WeChat Mini Program environments directly.
      // If not, we need a polyfill or a simple implementation.
      // For modern WeChat base library, TextDecoder is supported.
      
      try {
        const text = decodeURIComponent(escape(String.fromCharCode(...uint8Array)));
        if (onChunk) onChunk(text);
      } catch (e) {
        console.error("Error decoding chunk:", e);
        // Fallback or handle partial characters (advanced)
      }
    }
  });

  return requestTask;
};

// Simple polyfill-like behavior if needed, but try standard approach first.
