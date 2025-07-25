export default function WebsiteViewer() {
  return (
    <iframe
      src={props.url}
      className="w-full h-full border border-zinc-200 dark:border-zinc-800 rounded-lg shadow-md"
      sandbox="allow-scripts allow-same-origin allow-popups allow-forms"
      referrerpolicy="no-referrer"
    />
  );
}