// src/components/TerminalPanel.jsx
import React, { useState, useRef, useEffect } from 'react';
import { useStore } from '../store';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tooltip, TooltipContent, TooltipTrigger, TooltipProvider } from '@/components/ui/tooltip';
import { Send, Terminal, Bot, User, AlertCircle, CheckCircle, Loader2, Copy, Trash2, Info } from 'lucide-react';

const TerminalPanel = () => {
  const [input, setInput] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const scrollRef = useRef(null);
  
  const output = useStore((state) => state.output);
  const isRunning = useStore((state) => state.isRunning);
  const sendChatMessageToFlowBuilder = useStore((state) => state.sendChatMessageToFlowBuilder);
  
  const [messages, setMessages] = useState([
    { type: 'system', content: 'Welcome to Tesslate Agent Builder Terminal', timestamp: new Date() }
  ]);

  useEffect(() => {
    if (output && output !== "Output will appear here...") {
      setMessages(prev => [...prev, {
        type: 'output',
        content: output,
        timestamp: new Date()
      }]);
    }
  }, [output]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isProcessing) return;

    const userMessage = input.trim();
    setInput('');
    setIsProcessing(true);

    // Add user message
    setMessages(prev => [...prev, {
      type: 'user',
      content: userMessage,
      timestamp: new Date()
    }]);

    try {
      // Send to AI flow builder
      const response = await sendChatMessageToFlowBuilder(userMessage);
      
      if (response.reply) {
        setMessages(prev => [...prev, {
          type: 'assistant',
          content: response.reply,
          timestamp: new Date()
        }]);
      }
    } catch (error) {
      setMessages(prev => [...prev, {
        type: 'error',
        content: `Error: ${error.message}`,
        timestamp: new Date()
      }]);
    } finally {
      setIsProcessing(false);
    }
  };

  const clearMessages = () => {
    setMessages([
      { type: 'system', content: 'Terminal cleared', timestamp: new Date() }
    ]);
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
  };

  const getMessageIcon = (type) => {
    switch (type) {
      case 'user':
        return <User className="h-4 w-4" />;
      case 'assistant':
        return <Bot className="h-4 w-4" />;
      case 'system':
        return <Terminal className="h-4 w-4" />;
      case 'error':
        return <AlertCircle className="h-4 w-4 text-destructive" />;
      case 'output':
        return <CheckCircle className="h-4 w-4 text-success" />;
      default:
        return <Terminal className="h-4 w-4" />;
    }
  };

  const formatTimestamp = (date) => {
    return date.toLocaleTimeString('en-US', { 
      hour12: false, 
      hour: '2-digit', 
      minute: '2-digit', 
      second: '2-digit' 
    });
  };

  const formatContent = (content) => {
    // Handle special formatting for output
    if (content.includes('PREVIEW_LINK::')) {
      const parts = content.split('PREVIEW_LINK::');
      const link = parts[1]?.split('\n')[0];
      return (
        <>
          {parts[0]}
          {link && (
            <a 
              href={link} 
              target="_blank" 
              rel="noopener noreferrer"
              className="text-primary hover:underline"
            >
              Preview Generated File
            </a>
          )}
        </>
      );
    }
    return content;
  };

  return (
    <div className="flex flex-col h-full bg-sidebar">
      {/* Header */}
      <div className="h-14 flex items-center justify-between px-4 border-b border-sidebar-border flex-shrink-0">
        <div className="flex items-center space-x-2">
          <Terminal className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm font-medium">Terminal & AI Assistant</span>
        </div>
        <Button
          variant="ghost"
          size="icon"
          onClick={clearMessages}
          className="h-8 w-8"
        >
          <Trash2 className="h-4 w-4" />
        </Button>
      </div>

      {/* Messages - Fixed height with proper scrolling */}
      <div className="flex-1 overflow-hidden p-3">
        <div className="h-full bg-card/50 rounded-lg border border-border/50 overflow-hidden">
          <ScrollArea className="h-full">
            <div className="p-4 space-y-3">
            {messages.map((message, index) => (
              <div key={index} className="group animate-fade-in">
                <div className="flex items-start space-x-3">
                  <div className={`mt-0.5 p-1.5 rounded flex-shrink-0 ${
                    message.type === 'user' ? 'bg-primary/10 text-primary' :
                    message.type === 'assistant' ? 'bg-accent/10 text-accent' :
                    message.type === 'error' ? 'bg-destructive/10' :
                    'bg-muted/50 text-muted-foreground'
                  }`}>
                    {getMessageIcon(message.type)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-2 mb-1">
                      <span className="text-xs font-medium text-muted-foreground">
                        {message.type === 'user' ? 'You' :
                         message.type === 'assistant' ? 'AI Assistant' :
                         message.type === 'system' ? 'System' :
                         message.type === 'output' ? 'Flow Output' :
                         'Error'}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        {formatTimestamp(message.timestamp)}
                      </span>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => copyToClipboard(message.content)}
                        className="h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity"
                      >
                        <Copy className="h-3 w-3" />
                      </Button>
                    </div>
                    <div className={`text-sm whitespace-pre-wrap break-words max-w-full ${
                      message.type === 'output' ? 'font-mono text-xs' : ''
                    }`}>
                      {formatContent(message.content)}
                    </div>
                  </div>
                </div>
              </div>
            ))}
            {isProcessing && (
              <div className="flex items-center space-x-3 animate-fade-in">
                <div className="p-1.5 rounded bg-accent/10 text-accent">
                  <Loader2 className="h-4 w-4 animate-spin" />
                </div>
                <span className="text-sm text-muted-foreground">AI is thinking...</span>
              </div>
            )}
            <div ref={scrollRef} />
            </div>
          </ScrollArea>
        </div>
      </div>

      {/* Input */}
      <div className="border-t border-sidebar-border p-3 flex-shrink-0">
        <div className="flex items-center bg-card border border-border rounded-lg overflow-hidden">
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-10 w-10 flex-shrink-0 rounded-none hover:bg-muted/50"
                >
                  <Info className="h-4 w-4 text-muted-foreground" />
                </Button>
              </TooltipTrigger>
              <TooltipContent side="top" className="max-w-sm">
                <div className="space-y-1">
                  <p className="font-medium">Try these example prompts:</p>
                  <ul className="text-xs space-y-1">
                    <li>• "Create a weather agent that tells me today's forecast"</li>
                    <li>• "Make a recipe finder that suggests meals based on ingredients"</li>
                    <li>• "Build a travel planner that finds flights and hotels"</li>
                    <li>• "Create a news summarizer that reads articles and gives me key points"</li>
                    <li>• "Make a shopping assistant that compares prices across websites"</li>
                  </ul>
                </div>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
            placeholder="Ask AI to build a flow or type a command..."
            className="flex-1 border-0 bg-transparent focus-visible:ring-0 focus-visible:ring-offset-0 rounded-none h-10"
            disabled={isProcessing || isRunning}
          />
          <Button
            onClick={handleSend}
            size="icon"
            className="h-10 w-10 flex-shrink-0 rounded-none"
            disabled={!input.trim() || isProcessing || isRunning}
          >
            {isProcessing ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </div>
      </div>
    </div>
  );
};

export default TerminalPanel;