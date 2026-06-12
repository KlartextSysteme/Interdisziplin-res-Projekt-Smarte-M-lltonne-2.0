export default function Home() {
  return (
    <>
      <meta httpEquiv="refresh" content="0; url=/dashboard/" />
      <main className="flex min-h-screen items-center justify-center bg-[#151619] text-slate-200">
        <a className="rounded border border-[#f2c94c]/40 px-4 py-2 text-[#f2c94c]" href="/dashboard/">
          Dashboard öffnen
        </a>
      </main>
    </>
  );
}
