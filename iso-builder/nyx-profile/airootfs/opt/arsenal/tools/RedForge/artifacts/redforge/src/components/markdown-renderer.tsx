import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

export function MarkdownRenderer({ content, className = "" }: MarkdownRendererProps) {
  return (
    <div className={`prose prose-sm prose-invert max-w-none font-mono ${className}`}>
      <ReactMarkdown remarkPlugins={[remarkGfm]}>
        {content || "*No content*"}
      </ReactMarkdown>
    </div>
  );
}
