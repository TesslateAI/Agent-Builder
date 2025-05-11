// builder/frontend/src/components/CodeRegistrationPanel.jsx
import React, { useState } from 'react';
import { useStore } from '../store';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { CheckCircle, XCircle, Loader2, Terminal } from 'lucide-react';

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
  const registerTFrameXCode = useStore((state) => state.registerTFrameXCode);
  const isRegistering = useStore((state) => state.isRegisteringCode);
  const registrationStatus = useStore((state) => state.registrationStatus);

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
    <div className="space-y-4">
      <div>
        <Label htmlFor="pythonCode" className="text-sm font-medium">
          Python Code for TFrameX Agent or Tool
        </Label>
        <p className="text-xs text-muted-foreground mb-1">
          Use <code>@tframex_app.agent(...)</code> or <code>@tframex_app.tool(...)</code>.
        </p>
        <div className="flex space-x-2 mb-2">
            <Button variant="outline" size="sm" onClick={() => loadExample('agent')}>Load Agent Example</Button>
            <Button variant="outline" size="sm" onClick={() => loadExample('tool')}>Load Tool Example</Button>
        </div>
        <Textarea
          id="pythonCode"
          value={pythonCode}
          onChange={(e) => setPythonCode(e.target.value)}
          placeholder="Paste your TFrameX agent or tool definition here..."
          className="min-h-[200px] font-mono text-xs border-border"
          rows={15}
        />
      </div>
      <Button onClick={handleSubmit} disabled={isRegistering || !pythonCode.trim()} className="w-full">
        {isRegistering ? (
          <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Registering...</>
        ) : (
          "Register Component"
        )}
      </Button>

      {registrationStatus && (
        <Alert variant={registrationStatus.success ? "default" : "destructive"} className="mt-4">
          {registrationStatus.success ? <CheckCircle className="h-4 w-4" /> : <XCircle className="h-4 w-4" />}
          <AlertTitle>{registrationStatus.success ? "Success" : "Error"}</AlertTitle>
          <AlertDescription>{registrationStatus.message}</AlertDescription>
        </Alert>
      )}
       <Alert variant="default" className="mt-4">
          <Terminal className="h-4 w-4" />
          <AlertTitle>Important Notes</AlertTitle>
          <AlertDescription>
            <ul className="list-disc list-inside text-xs space-y-1">
                <li>Code is executed on the backend. Ensure it's safe.</li>
                <li>Use the global <code>tframex_app</code> variable for decorators (e.g., <code>@tframex_app.agent(...)</code>).</li>
                <li>Necessary imports (like <code>OpenAIChatLLM</code>, <code>Message</code> from <code>tframex</code>, <code>asyncio</code>, <code>os</code>) are available in the execution scope.</li>
                <li>After successful registration, new components will appear in the "Components" tab (may require a manual refresh of that tab or auto-refresh).</li>
            </ul>
          </AlertDescription>
        </Alert>
    </div>
  );
};

export default CodeRegistrationPanel;