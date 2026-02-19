import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

const protectedRoutes = ['/profile', '/debates'];
const publicRoutes = ['/login', '/register'];

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Check if route is protected
  const isProtectedRoute = protectedRoutes.some((route) =>
    pathname.startsWith(route)
  );

  // Check if route is public (auth related)
  const isPublicRoute = publicRoutes.some((route) =>
    pathname.startsWith(route)
  );

  const accessToken = request.cookies.get('access_token')?.value;
  const refreshToken = request.cookies.get('refresh_token')?.value;
  
  // Design decision: We consider user "potentially" authenticated if they have
  // either an access token OR a refresh token.
  // If access token is expired, the client-side axios interceptor will handle the refresh.
  // If we block here because missing access_token (but has refresh_token), 
  // we break the seamless refresh flow on hard navigations.
  const isAuthenticated = !!accessToken || !!refreshToken;

  // 1. Redirect unauthenticated users from protected routes to login
  if (isProtectedRoute && !isAuthenticated) {
    const loginUrl = new URL('/login', request.url);
    // Optionally add ?from=pathname to redirect back after login
    return NextResponse.redirect(loginUrl);
  }

  // 2. Redirect authenticated users from public auth routes (login/register) to profile (or home)
  if (isPublicRoute && isAuthenticated) {
    return NextResponse.redirect(new URL('/debates', request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico, sitemap.xml, robots.txt (metadata files)
     */
    '/((?!api|_next/static|_next/image|favicon.ico|sitemap.xml|robots.txt).*)',
  ],
};
