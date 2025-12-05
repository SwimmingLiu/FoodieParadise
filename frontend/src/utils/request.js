/**
 * Custom request utility for WeChat Mini Program to support Chunked Transfer Encoding
 * Simulates SSE (Server-Sent Events) behavior with proper buffering
 */

/**
 * Parse SSE formatted text into structured events
 * @param {string} text - Raw SSE text
 * @returns {Array<{event: string, data: string}>} Parsed events
 */
const parseSSEEvents = (text) => {
  const events = [];
  // Split by double newline (SSE event delimiter)
  const rawEvents = text.split(/\n\n/);
  
  for (const rawEvent of rawEvents) {
    if (!rawEvent.trim()) continue;
    
    let event = 'message'; // default event type
    let data = '';
    
    const lines = rawEvent.split('\n');
    for (const line of lines) {
      if (line.startsWith('event: ')) {
        event = line.substring(7).trim();
      } else if (line.startsWith('data: ')) {
        data += line.substring(6);
      } else if (line.startsWith('data:')) {
        // Handle case where data: has no space after colon
        data += line.substring(5);
      }
    }
    
    if (data) {
      events.push({ event, data });
    }
  }
  
  return events;
};

/**
 * Stream request with SSE support and proper buffering
 * Handles chunked transfer encoding for WeChat Mini Program
 */
export const streamRequest = ({ url, method = 'GET', data = {}, header = {}, onEvent, onChunk, onComplete, onError }) => {
  // Buffer for incomplete SSE events across chunks
  let buffer = '';
  
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
      // Process any remaining buffer content
      if (buffer.trim()) {
        const events = parseSSEEvents(buffer);
        for (const evt of events) {
          if (onEvent) onEvent(evt.event, evt.data);
        }
      }
      if (onComplete) onComplete(res);
    },
    fail: (err) => {
      if (onError) onError(err);
    }
  });

  // Listen for chunks
  requestTask.onChunkReceived((response) => {
    if (response.data) {
      const uint8Array = new Uint8Array(response.data);

      try {
        let text;
        if (typeof TextDecoder !== 'undefined') {
          const decoder = new TextDecoder('utf-8');
          text = decoder.decode(uint8Array, { stream: true });
        } else {
          // Fallback for environments without TextDecoder
          text = decodeURIComponent(escape(String.fromCharCode(...uint8Array)));
        }
        
        // Add to buffer
        buffer += text;
        
        // Find complete SSE events (ending with \n\n)
        const lastDoubleNewline = buffer.lastIndexOf('\n\n');
        
        if (lastDoubleNewline !== -1) {
          // Extract complete events
          const completeText = buffer.substring(0, lastDoubleNewline + 2);
          // Keep incomplete part in buffer
          buffer = buffer.substring(lastDoubleNewline + 2);
          
          // Parse and emit events
          const events = parseSSEEvents(completeText);
          for (const evt of events) {
            if (onEvent) onEvent(evt.event, evt.data);
          }
          
          // Also call legacy onChunk for backward compatibility
          if (onChunk) onChunk(completeText);
        }
      } catch (e) {
        console.error("Error decoding chunk:", e);
      }
    }
  });

  return requestTask;
};
