/**
 * Renders common markdown used in AI-generated task descriptions
 * (headings, lists, paragraphs, bold) without a heavy dependency.
 */

function formatInline(text) {
    const parts = text.split(/(\*\*[^*]+\*\*)/g);
    return parts.map((part, i) => {
        if (part.startsWith("**") && part.endsWith("**")) {
            return <strong key={i}>{part.slice(2, -2)}</strong>;
        }
        return part;
    });
}

export default function TaskDescriptionMarkdown({ text }) {
    if (!text?.trim()) return null;

    const lines = text.replace(/\r\n/g, "\n").split("\n");
    const blocks = [];
    let listItems = [];
    let key = 0;

    const nextKey = () => {
        key += 1;
        return key;
    };

    const flushList = () => {
        if (listItems.length === 0) return;
        blocks.push(
            <ul key={nextKey()} className="kb-prose-list">
                {listItems}
            </ul>
        );
        listItems = [];
    };

    for (const line of lines) {
        const trimmed = line.trim();

        if (!trimmed) {
            flushList();
            continue;
        }

        const h3 = trimmed.match(/^###\s+(.+)$/);
        const h2 = trimmed.match(/^##\s+(.+)$/);
        const h1 = trimmed.match(/^#\s+(.+)$/);
        const bullet = trimmed.match(/^[-*]\s+(.+)$/);

        if (h3 || h2 || h1) {
            flushList();
            const content = (h3 || h2 || h1)[1];
            if (h3) {
                blocks.push(
                    <h4 key={nextKey()} className="kb-prose-h4">
                        {formatInline(content)}
                    </h4>
                );
            } else if (h2) {
                blocks.push(
                    <h3 key={nextKey()} className="kb-prose-h3">
                        {formatInline(content)}
                    </h3>
                );
            } else {
                blocks.push(
                    <h2 key={nextKey()} className="kb-prose-h2">
                        {formatInline(content)}
                    </h2>
                );
            }
            continue;
        }

        if (bullet) {
            listItems.push(
                <li key={nextKey()}>{formatInline(bullet[1])}</li>
            );
            continue;
        }

        flushList();
        blocks.push(
            <p key={nextKey()} className="kb-prose-p">
                {formatInline(trimmed)}
            </p>
        );
    }

    flushList();

    return <div className="kb-detail-prose">{blocks}</div>;
}
