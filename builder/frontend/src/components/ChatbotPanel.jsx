// src/components/ChatbotPanel.jsx
import React, { useState, useRef, useEffect } from 'react';
import { useStore } from '../store';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area'; // Use shadcn ScrollArea
import { Send, Trash2, Loader2 } from 'lucide-react'; // Icons
import { cn } from '@/lib/utils'; // Import cn utility

const ChatbotPanel = () => {
  const [inputMessage, setInputMessage] = useState('');
  const chatHistory = useStore((state) => state.chatHistory);
  const sendChatMessage = useStore((state) => state.sendChatMessage);
  const isChatbotLoading = useStore((state) => state.isChatbotLoading);
  const clearChatHistory = useStore((state) => state.clearChatHistory);
  const messagesEndRef = useRef(null);
  const scrollAreaViewportRef = useRef(null);

  // Scroll to bottom when new messages arrive or loading state changes
  useEffect(() => {
    const viewport = scrollAreaViewportRef.current;
    if (viewport) {
        // Use setTimeout to allow the DOM to update before scrolling
        setTimeout(() => {
             viewport.scrollTo({ top: viewport.scrollHeight, behavior: 'smooth' });
        }, 50); // Short delay
    }
  }, [chatHistory, isChatbotLoading]); // Trigger on history and loading state

  const handleSendMessage = (e) => {
    e.preventDefault();
    if (inputMessage.trim() && !isChatbotLoading) {
      sendChatMessage(inputMessage.trim());
      setInputMessage('');
    }
  };

  return (
    <div className="flex flex-col h-full p-3"> {/* Add padding to the panel */}
      {/* Chat History */}
      <ScrollArea className="flex-grow mb-3 rounded-md border border-border bg-background">
         <div ref={scrollAreaViewportRef} className="h-full p-3 space-y-4"> {/* Add padding inside scroll area */}
            {chatHistory.map((msg, index) => (
              <div key={index} className={cn('flex', msg.sender === 'user' ? 'justify-end' : 'justify-start')}>
                <div
                  className={cn(
                    'max-w-[80%] p-2.5 rounded-lg text-sm whitespace-pre-wrap break-words shadow-sm', // Added shadow
                    msg.sender === 'user'
                      ? 'bg-primary text-primary-foreground'
                      : msg.type === 'error'
                      ? 'bg-destructive text-destructive-foreground'
                      : 'bg-secondary text-secondary-foreground' // Default bot message
                  )}
                >
                  {msg.message}
                </div>
              </div>
            ))}
             {isChatbotLoading && (
                 <div className="flex justify-start">
                     <div className="max-w-[80%] p-2.5 rounded-lg text-sm bg-secondary text-muted-foreground flex items-center">
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Thinking...
                     </div>
                 </div>
             )}
            <div ref={messagesEndRef} /> {/* Invisible element to scroll to */}
         </div>
      </ScrollArea>

      {/* Input Area */}
      <form onSubmit={handleSendMessage} className="flex-shrink-0 flex items-center space-x-2">
        <Input
          type="text"
          value={inputMessage}
          onChange={(e) => setInputMessage(e.target.value)}
          placeholder="Describe the flow..."
          className="flex-grow" // Removed !mt-0 as margin handled by space-x
          disabled={isChatbotLoading}
          aria-label="Chat input"
        />
        <Button
          type="submit"
          size="icon"
          disabled={isChatbotLoading || !inputMessage.trim()}
          title="Send Message"
        >
          <Send className="h-4 w-4" />
          <span className="sr-only">Send</span>
        </Button>
         <Button
            type="button"
            variant="outline"
            size="icon"
            onClick={clearChatHistory}
            disabled={isChatbotLoading || chatHistory.length === 0}
            title="Clear Chat"
        >
            <Trash2 className="h-4 w-4" />
            <span className="sr-only">Clear Chat</span>
        </Button>
      </form>
    </div>
  );
};

export default ChatbotPanel;