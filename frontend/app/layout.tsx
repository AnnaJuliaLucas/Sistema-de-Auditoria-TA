"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import "./globals.css";
import Sidebar from "@/components/Sidebar";

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const pathname = usePathname();
  const router = useRouter();
  const [authorized, setAuthorized] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("audit_token");
    const isLoginPage = pathname === "/login";

    if (!token && !isLoginPage) {
      router.push("/login");
    } else {
      setAuthorized(true);
    }
  }, [pathname, router]);

  const isLoginPage = pathname === "/login";

  return (
    <html lang="pt-BR">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="flex min-h-screen bg-[#0f172a]">
        {!isLoginPage && authorized && <Sidebar />}
        <main className={`flex-1 ${!isLoginPage ? "ml-64" : ""} p-8 overflow-y-auto`}>
          {isLoginPage ? children : (authorized ? children : (
            <div className="flex items-center justify-center h-screen">
              <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
            </div>
          ))}
        </main>
      </body>
    </html>
  );
}
