/**
 * Custom request utility for WeChat Mini Program to support Chunked Transfer Encoding
 * Simulates SSE (Server-Sent Events) behavior with proper buffering
 * 
 * Key features:
 * - Handles UTF-8 multi-byte character boundaries across chunks
 * - Buffers incomplete SSE events until complete
 * - Parses SSE event/data format properly
 */

/**
 * Parse SSE formatted text into structured events
 * Handles multi-line data by joining multiple data: lines with newlines
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
    const dataLines = []; // Collect all data lines
    
    const lines = rawEvent.split('\n');
    for (const line of lines) {
      if (line.startsWith('event: ')) {
        event = line.substring(7).trim();
      } else if (line.startsWith('data: ')) {
        // Add data content (with proper newline handling for multi-line data)
        dataLines.push(line.substring(6));
      } else if (line.startsWith('data:')) {
        // Handle case where data: has no space after colon
        dataLines.push(line.substring(5));
      }
    }
    
    // Join multiple data lines with newlines (SSE spec)
    const data = dataLines.join('\n');
    
    if (data) {
      events.push({ event, data });
    }
  }
  
  return events;
};

/**
 * Stream request with SSE support and proper buffering
 * Handles chunked transfer encoding for WeChat Mini Program
 * 
 * IMPORTANT: Uses persistent TextDecoder to handle UTF-8 multi-byte
 * characters that may be split across chunk boundaries
 */
export const streamRequest = ({ url, method = 'GET', data = {}, header = {}, onEvent, onChunk, onComplete, onError }) => {
  // Buffer for incomplete SSE events across chunks
  let buffer = '';
  
  // Buffer for incomplete UTF-8 bytes (for environments without streaming TextDecoder)
  let byteBuffer = new Uint8Array(0);
  
  // Create a persistent TextDecoder for streaming (handles multi-byte char boundaries)
  let decoder;
  try {
    decoder = new TextDecoder('utf-8', { fatal: false });
  } catch (e) {
    decoder = null;
  }
  
  /**
   * Decode bytes to string, handling UTF-8 multi-byte character boundaries
   * @param {Uint8Array} bytes - New bytes to decode
   * @param {boolean} flush - Whether to flush remaining bytes (stream end)
   * @returns {string} Decoded string
   */
  const decodeBytes = (bytes, flush = false) => {
    if (decoder) {
      // Use TextDecoder with stream mode to handle character boundaries
      return decoder.decode(bytes, { stream: !flush });
    } else {
      // Fallback: Concatenate bytes and decode complete UTF-8 sequences only
      const combined = new Uint8Array(byteBuffer.length + bytes.length);
      combined.set(byteBuffer);
      combined.set(bytes, byteBuffer.length);
      
      // Find the last complete UTF-8 character boundary
      let validEnd = combined.length;
      for (let i = combined.length - 1; i >= Math.max(0, combined.length - 4); i--) {
        const byte = combined[i];
        // Check if this is a UTF-8 leading byte (not a continuation byte 10xxxxxx)
        if ((byte & 0xC0) !== 0x80) {
          // Found leading byte, check if sequence is complete
          let expectedLen = 1;
          if ((byte & 0xF0) === 0xF0) expectedLen = 4;
          else if ((byte & 0xE0) === 0xE0) expectedLen = 3;
          else if ((byte & 0xC0) === 0xC0) expectedLen = 2;
          
          if (i + expectedLen <= combined.length) {
            validEnd = combined.length;
          } else {
            validEnd = i;
          }
          break;
        }
      }
      
      if (flush) {
        validEnd = combined.length;
        byteBuffer = new Uint8Array(0);
      } else {
        byteBuffer = combined.slice(validEnd);
      }
      
      const validBytes = combined.slice(0, validEnd);
      try {
        return decodeURIComponent(escape(String.fromCharCode.apply(null, validBytes)));
      } catch (e) {
        // If decoding fails, try simple conversion
        let result = '';
        for (let i = 0; i < validBytes.length; i++) {
          result += String.fromCharCode(validBytes[i]);
        }
        return result;
      }
    }
  };
  
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
      // Flush any remaining bytes
      if (byteBuffer.length > 0 && decoder) {
        buffer += decoder.decode(new Uint8Array(0), { stream: false });
      }
      
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
        // Decode with proper UTF-8 multi-byte handling
        const text = decodeBytes(uint8Array, false);
        
        if (!text) return; // No complete characters yet
        
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
