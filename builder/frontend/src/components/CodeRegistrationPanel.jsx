// builder/frontend/src/components/CodeRegistrationPanel.jsx
import React, { useState, useRef } from 'react';
import { createPortal } from 'react-dom';
import { useStore } from '../store';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { CheckCircle, XCircle, Loader2, Terminal, HelpCircle, ChevronDown, ChevronRight } from 'lucide-react';

const EXAMPLE_AGENT_CODE = `
# Example TFrameX Agent
# Ensure 'tframex_app' is used for the decorator.
@tframex_app.agent(
    name="MyCustomEchoAgent",
    description="A custom agent that echoes input with a prefix.",
    system_prompt="You are an echo assistant. Prefix any user message with 'CustomEcho: '."
)
async def my_custom_echo_agent_placeholder():
    pass # TFrameX LLMAgent handles the logic
`.trim();

const EXAMPLE_TOOL_CODE = `
# Example TFrameX Tool
# Ensure 'tframex_app' is used for the decorator.
@tframex_app.tool(
    name="my_custom_math_tool",
    description="Performs a simple addition of two numbers."
)
async def my_custom_math_tool_func(a: int, b: int) -> str:
    result = a + b
    return f"The sum of {a} and {b} is {result}."
`.trim();


const CodeRegistrationPanel = () => {
  const [pythonCode, setPythonCode] = useState(EXAMPLE_AGENT_CODE); // Default to agent example
  const [showTooltip, setShowTooltip] = useState(false);
  const [showImportantNotes, setShowImportantNotes] = useState(false);
  const [tooltipPosition, setTooltipPosition] = useState({ x: 0, y: 0 });
  const helpButtonRef = useRef(null);
  const registerTFrameXCode = useStore((state) => state.registerTFrameXCode);
  const isRegistering = useStore((state) => state.isRegisteringCode);
  const registrationStatus = useStore((state) => state.registrationStatus);

  const updateTooltipPosition = () => {
    if (helpButtonRef.current) {
      const rect = helpButtonRef.current.getBoundingClientRect();
      setTooltipPosition({
        x: rect.left,
        y: rect.bottom + 4
      });
    }
  };

  const handleMouseEnter = () => {
    updateTooltipPosition();
    setShowTooltip(true);
  };

  const handleSubmit = async () => {
    if (!pythonCode.trim()) {
      alert("Please enter Python code to register.");
      return;
    }
    await registerTFrameXCode(pythonCode);
    // Status will be updated in the store, triggering re-render
  };
  
  const loadExample = (type) => {
      if (type === 'agent') setPythonCode(EXAMPLE_AGENT_CODE);
      else if (type === 'tool') setPythonCode(EXAMPLE_TOOL_CODE);
  }

  return (
    <div className="p-3 space-y-3 flex flex-col h-full">
      <div className="space-y-3">
        <div className="flex items-center gap-2">
          <Label htmlFor="pythonCode" className="text-xs font-semibold text-foreground-muted uppercase tracking-wider">
            Python Code
          </Label>
          <div className="relative">
            <Button
              ref={helpButtonRef}
              variant="ghost"
              size="sm"
              className="h-5 w-5 p-0 hover:bg-hover text-foreground-subtle hover:text-foreground-muted transition-colors"
              onMouseEnter={handleMouseEnter}
              onMouseLeave={() => setShowTooltip(false)}
            >
              <HelpCircle className="h-3 w-3" />
            </Button>
            {showTooltip && createPortal(
              <div 
                className="fixed z-[9999] w-56 p-3 text-xs bg-surface-elevated border border-border rounded-lg shadow-xl pointer-events-none"
                style={{
                  left: `${tooltipPosition.x}px`,
                  top: `${tooltipPosition.y}px`
                }}
              >
                Use <code className="bg-surface text-info px-1.5 py-0.5 rounded font-mono text-[10px]">@tframex_app.agent(...)</code> or <code className="bg-surface text-info px-1.5 py-0.5 rounded font-mono text-[10px]">@tframex_app.tool(...)</code>
              </div>,
              document.body
            )}
          </div>
        </div>
        
        <div className="flex gap-2">
          <Button 
            variant="outline" 
            size="sm" 
            onClick={() => loadExample('agent')} 
            className="h-8 text-xs flex-1 bg-transparent border-border hover:bg-hover hover:border-border-strong text-foreground-subtle hover:text-foreground-muted transition-all rounded-md font-medium"
          >
            Agent Example
          </Button>
          <Button 
            variant="outline" 
            size="sm" 
            onClick={() => loadExample('tool')} 
            className="h-8 text-xs flex-1 bg-transparent border-border hover:bg-hover hover:border-border-strong text-foreground-subtle hover:text-foreground-muted transition-all rounded-md font-medium"
          >
            Tool Example
          </Button>
        </div>
      </div>

      <div className="flex-1 min-h-0">
        <Textarea
          id="pythonCode"
          value={pythonCode}
          onChange={(e) => setPythonCode(e.target.value)}
          placeholder="Paste your TFrameX agent or tool definition here..."
          className="h-full font-mono text-xs bg-input border-border text-foreground placeholder-foreground-subtle resize-none rounded-lg focus:ring-2 focus:ring-primary/30 focus:border-primary/50 transition-all"
        />
      </div>
      
      <div className="space-y-3">
        <Button 
          onClick={handleSubmit} 
          disabled={isRegistering || !pythonCode.trim()} 
          className="w-full h-9 bg-primary hover:bg-primary-hover text-primary-foreground rounded-lg font-medium transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {isRegistering ? (
            <><Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" /> Registering...</>
          ) : (
            "Register Component"
          )}
        </Button>

        {registrationStatus && (
          <Alert 
            variant={registrationStatus.success ? "default" : "destructive"} 
            className={`rounded-lg border-l-4 ${
              registrationStatus.success 
                ? 'bg-success/10 border-success' 
                : 'bg-error/10 border-error'
            }`}
          >
            {registrationStatus.success ? 
              <CheckCircle className="h-3.5 w-3.5 text-success" /> : 
              <XCircle className="h-3.5 w-3.5 text-error" />
            }
            <AlertTitle className={registrationStatus.success ? "text-success text-xs" : "text-error text-xs"}>
              {registrationStatus.success ? "Success" : "Error"}
            </AlertTitle>
            <AlertDescription className="text-xs text-foreground-subtle mt-1">
              {registrationStatus.message}
            </AlertDescription>
          </Alert>
        )}

        {/* Collapsible Important Notes */}
        <div className="border border-border rounded-lg overflow-hidden bg-card/50">
          <button
            onClick={() => setShowImportantNotes(!showImportantNotes)}
            className="w-full flex items-center justify-between p-2.5 text-left hover:bg-hover transition-all duration-200"
          >
            <div className="flex items-center gap-2">
              <Terminal className="h-3.5 w-3.5 text-info" />
              <span className="text-xs font-medium text-foreground">Important Notes</span>
            </div>
            {showImportantNotes ? (
              <ChevronDown className="h-3.5 w-3.5 text-foreground-subtle transition-transform duration-200" />
            ) : (
              <ChevronRight className="h-3.5 w-3.5 text-foreground-subtle transition-transform duration-200" />
            )}
          </button>
          {showImportantNotes && (
            <div className="px-3 pb-3 text-xs text-foreground-muted border-t border-border bg-surface/50">
              <ul className="space-y-1.5 mt-2">
                <li className="flex items-start gap-2">
                  <span className="text-info mt-0.5">▸</span>
                  <span>Code executes on backend - ensure safety</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-info mt-0.5">▸</span>
                  <span>Use global <code className="bg-surface text-info px-1 py-0.5 rounded text-[10px] font-mono">tframex_app</code> variable</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-info mt-0.5">▸</span>
                  <span>Common imports available in scope</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-info mt-0.5">▸</span>
                  <span>New components appear in Components tab</span>
                </li>
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default CodeRegistrationPanel;