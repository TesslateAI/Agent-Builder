// src/components/OutputPanel.jsx
import React from 'react';
import { useStore } from '../store';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from '@/components/ui/scroll-area';
import { Trash2, ExternalLink } from 'lucide-react'; // Import ExternalLink

const OutputPanel = () => {
  const output = useStore((state) => state.output);
  const clearOutput = useStore((state) => state.clearOutput);
  const isRunning = useStore((state) => state.isRunning);

  const hasContent = output && output !== "Output will appear here..." && output.trim() !== "";

  // --- NEW: Detect Preview Link ---
  let previewLink = null;
  let cleanedOutput = output; // Output without the preview marker line
  if (hasContent) {
      const linkMarker = "PREVIEW_LINK::";
      const linkIndex = output.indexOf(linkMarker);
      if (linkIndex !== -1) {
          const linkLine = output.substring(linkIndex + linkMarker.length);
          // Extract the link (assuming it's the rest of the line)
          const linkMatch = linkLine.match(/(\/api\/preview\/.*)/);
          if (linkMatch && linkMatch[1]) {
               const relativePreviewLink = linkMatch[1].trim();
               previewLink = `http://localhost:5001${relativePreviewLink}`; // Prepend the base URL
               // Remove the marker line and potentially the user-friendly message line below it from the displayed output
               const lines = output.split('\n');
               cleanedOutput = lines.filter(line => !line.startsWith(linkMarker) && !line.includes("(Link to preview generated content:")).join('\n');
          } else {
              // If marker exists but link extraction fails, keep original output
               cleanedOutput = output;
          }
      } else {
          cleanedOutput = output;
      }
  }
  // --- END NEW ---

  return (
    <Card className="w-[450px] flex flex-col rounded-none border-l border-t-0 border-b-0 border-r-0 border-border h-full shadow-none">
       <CardHeader className="flex flex-row justify-between items-center p-3 border-b border-border flex-shrink-0 h-16">
            <CardTitle className="text-lg font-semibold">Output</CardTitle>
            {/* --- NEW: Add Preview Button --- */}
            {previewLink && (
                 <Button
                    variant="secondary" // Or another variant
                    size="sm"
                    onClick={() => window.open(previewLink, '_blank')}
                    title="Open Preview in New Tab"
                  >
                    <ExternalLink className="h-4 w-4 mr-1" /> Preview
                 </Button>
            )}
            {/* --- END NEW --- */}
            <Button
                variant="outline"
                size="sm"
                onClick={clearOutput}
                disabled={isRunning || !hasContent}
                className="ml-auto" // Push clear button to the right if preview exists
            >
                <Trash2 className="h-4 w-4 mr-1" /> Clear
            </Button>
       </CardHeader>

      <CardContent className="flex-grow p-0 overflow-hidden">
        <ScrollArea className="h-full w-full">
            <pre className="text-sm text-muted-foreground whitespace-pre-wrap break-words font-mono p-4">
                 {/* Display cleanedOutput */}
                {hasContent ? cleanedOutput : <span className="text-muted-foreground/70 italic">Output will appear here...</span>}
            </pre>
        </ScrollArea>
      </CardContent>
    </Card>
  );
};

export default OutputPanel;