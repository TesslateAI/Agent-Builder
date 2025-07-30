// builder/frontend/src/components/CodeRegistrationPanel.jsx
import React, { useState, useRef, useEffect } from 'react';
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
    <div className="p-4 space-y-3 flex flex-col h-full">
      <div className="space-y-3">
        <div className="flex items-center gap-2">
          <Label htmlFor="pythonCode" className="text-sm font-medium text-foreground">
            Python Code for TFrameX
          </Label>
          <div className="relative">
            <Button
              ref={helpButtonRef}
              variant="ghost"
              size="sm"
              className="h-6 w-6 p-0 hover:bg-muted"
              onMouseEnter={handleMouseEnter}
              onMouseLeave={() => setShowTooltip(false)}
            >
              <HelpCircle className="h-3 w-3" />
            </Button>
            {showTooltip && createPortal(
              <div 
                className="fixed z-[9999] w-48 p-2 text-xs bg-popover border border-border rounded-md shadow-lg pointer-events-none"
                style={{
                  left: `${tooltipPosition.x}px`,
                  top: `${tooltipPosition.y}px`
                }}
              >
                Use <code className="bg-muted px-1 py-0.5 rounded">@tframex_app.agent(...)</code> or <code className="bg-muted px-1 py-0.5 rounded">@tframex_app.tool(...)</code>
              </div>,
              document.body
            )}
          </div>
        </div>
        
        <div className="flex gap-2">
          <Button variant="secondary" size="sm" onClick={() => loadExample('agent')} className="h-8 text-xs flex-1 rounded-lg hover:bg-secondary/80 transition-colors">
            Agent Example
          </Button>
          <Button variant="secondary" size="sm" onClick={() => loadExample('tool')} className="h-8 text-xs flex-1 rounded-lg hover:bg-secondary/80 transition-colors">
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
          className="h-full font-mono text-xs bg-background border-border resize-none rounded-lg focus:ring-2 focus:ring-primary/20 transition-all"
        />
      </div>
      
      <div className="space-y-3">
        <Button 
          onClick={handleSubmit} 
          disabled={isRegistering || !pythonCode.trim()} 
          className="w-full h-10 bg-primary hover:bg-primary/90 rounded-lg font-medium transition-all duration-200 disabled:opacity-50"
        >
          {isRegistering ? (
            <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Registering...</>
          ) : (
            "Register Component"
          )}
        </Button>

        {registrationStatus && (
          <Alert variant={registrationStatus.success ? "default" : "destructive"} className="rounded-lg border-l-4">
            {registrationStatus.success ? <CheckCircle className="h-4 w-4" /> : <XCircle className="h-4 w-4" />}
            <AlertTitle>{registrationStatus.success ? "Success" : "Error"}</AlertTitle>
            <AlertDescription className="text-xs">{registrationStatus.message}</AlertDescription>
          </Alert>
        )}

        {/* Collapsible Important Notes */}
        <div className="border border-border rounded-lg overflow-hidden bg-card/30">
          <button
            onClick={() => setShowImportantNotes(!showImportantNotes)}
            className="w-full flex items-center justify-between p-3 text-left hover:bg-muted/30 transition-all duration-200"
          >
            <div className="flex items-center gap-2">
              <Terminal className="h-4 w-4 text-muted-foreground" />
              <span className="text-xs font-medium">Important Notes</span>
            </div>
            {showImportantNotes ? (
              <ChevronDown className="h-4 w-4 text-muted-foreground transition-transform duration-200" />
            ) : (
              <ChevronRight className="h-4 w-4 text-muted-foreground transition-transform duration-200" />
            )}
          </button>
          {showImportantNotes && (
            <div className="px-3 pb-3 text-xs text-muted-foreground border-t border-border/50 bg-muted/10">
              <ul className="space-y-1.5 mt-2">
                <li className="flex items-start gap-2">
                  <span className="text-primary">•</span>
                  <span>Code executes on backend - ensure safety</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-primary">•</span>
                  <span>Use global <code className="bg-muted px-1.5 py-0.5 rounded-md text-[11px]">tframex_app</code> variable</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-primary">•</span>
                  <span>Common imports available in scope</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-primary">•</span>
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