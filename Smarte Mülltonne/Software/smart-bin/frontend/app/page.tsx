export default function Home() {
  return (
    <>
      <meta httpEquiv="refresh" content="0; url=/dashboard/" />
      <main className="min-h-screen flex items-center justify-center bg-slate-50 text-slate-700">
        <a className="text-blue-600 underline" href="/dashboard/">
          Dashboard öffnen
        </a>
      </main>
    </>
  );
}
