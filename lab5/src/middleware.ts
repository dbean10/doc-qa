import { NextRequest, NextResponse } from 'next/server'

export function middleware(req: NextRequest) {
  console.log('[middleware] hit:', req.nextUrl.pathname)

  const authHeader = req.headers.get('authorization')

  if (!authHeader?.startsWith('Basic ')) {
    return new NextResponse('Unauthorized', {
      status: 401,
      headers: { 'WWW-Authenticate': 'Basic realm="Admin"' },
    })
  }

  const base64 = authHeader.slice('Basic '.length)
  const decoded = Buffer.from(base64, 'base64').toString('utf-8')
  const [user, ...rest] = decoded.split(':')
  const pass = rest.join(':')

  const validUser = process.env.ADMIN_USER
  const validPass = process.env.ADMIN_PASSWORD

  if (!validUser || !validPass || user !== validUser || pass !== validPass) {
    return new NextResponse('Unauthorized', {
      status: 401,
      headers: { 'WWW-Authenticate': 'Basic realm="Admin"' },
    })
  }

  return NextResponse.next()
}

export const config = {
  matcher: '/admin/:path*',
}
