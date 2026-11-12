export default function Offline() {
  return (
    <main className="mx-auto flex max-w-md flex-1 flex-col items-center justify-center gap-4 px-6 text-center">
      <h1 className="text-2xl font-bold">You are offline</h1>
      <p className="text-muted-foreground">VITALIS needs a connection to find a hospital. If this is an emergency, call now.</p>
      <a href="tel:112" className="flex min-h-16 w-full items-center justify-center rounded-2xl border-2 border-emergency bg-card text-xl font-bold text-emergency">
        Call 112
      </a>
    </main>
  );
}
