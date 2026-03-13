import { handleUpload, type HandleUploadBody } from '@vercel/blob/client';
import { NextResponse } from 'next/server';

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization',
};

export async function OPTIONS() {
  return NextResponse.json({}, { headers: corsHeaders });
}

export async function POST(request: Request): Promise<NextResponse> {
  const body = (await request.json()) as HandleUploadBody;

  try {
    const jsonResponse = await handleUpload({
      body,
      request,
      onBeforeGenerateToken: async (pathname) => {
        // Removes max 4.5MB SDK default so 200MB zip can pass security token validation
        return {
          maximumSizeInBytes: 500 * 1024 * 1024, 
          tokenPayload: JSON.stringify({}),
        };
      },
      onUploadCompleted: async ({ blob, tokenPayload }) => {
        console.log('Upload para Vercel Blob concluído com sucesso:', blob.url);
      },
    });

    return NextResponse.json(jsonResponse, { headers: corsHeaders });
  } catch (error) {
    return NextResponse.json(
      { error: (error as Error).message },
      { status: 400, headers: corsHeaders },
    );
  }
}
