/**
 * Lightweight markdown renderer for standup reports (headings, bullets, paragraphs).
 */
function StandupMarkdown({ text }) {
  if (!text || !String(text).trim()) {
    return <p className="tp-muted">No content</p>;
  }

  const blocks = [];
  let listItems = [];
  const lines = String(text).split("\n");

  const flushList = () => {
    if (listItems.length) {
      blocks.push(
        <ul key={`ul-${blocks.length}`} className="tp-standup-md__list">
          {listItems}
        </ul>
      );
      listItems = [];
    }
  };

  lines.forEach((line, index) => {
    const trimmed = line.trim();

    if (!trimmed) {
      flushList();
      return;
    }

    if (trimmed.startsWith("### ")) {
      flushList();
      blocks.push(
        <h4 key={index} className="tp-standup-md__h4">
          {trimmed.slice(4)}
        </h4>
      );
      return;
    }

    if (trimmed.startsWith("## ")) {
      flushList();
      blocks.push(
        <h3 key={index} className="tp-standup-md__h3">
          {trimmed.slice(3)}
        </h3>
      );
      return;
    }

    if (trimmed.startsWith("# ")) {
      flushList();
      blocks.push(
        <h2 key={index} className="tp-standup-md__h2">
          {trimmed.slice(2)}
        </h2>
      );
      return;
    }

    if (trimmed.startsWith("- ")) {
      listItems.push(
        <li key={index}>{trimmed.slice(2)}</li>
      );
      return;
    }

    flushList();
    blocks.push(
      <p key={index} className="tp-standup-md__p">
        {trimmed}
      </p>
    );
  });

  flushList();

  return <div className="tp-standup-md">{blocks}</div>;
}

export default StandupMarkdown;
