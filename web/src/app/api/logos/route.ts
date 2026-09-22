import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

export interface LogoItem {
  id: string;
  name: string;
  file: string;
  src: string;
}

const BRAND_NAME_MAP: Record<string, string> = {
  jade: 'Jade',
  doctorshield: 'DoctorShield',
  jaguar: 'Jaguar Transit',
  'jaguar-transit': 'Jaguar Transit',
  ja: 'JA Assure',
  'ja-assure': 'JA Assure',
};

export async function GET() {
  try {
    const logosDir = path.join(process.cwd(), 'public', 'logos');
    
    // Ensure directory exists, fallback to public/logo if not
    let dirToRead = logosDir;
    if (!fs.existsSync(logosDir)) {
      const fallbackDir = path.join(process.cwd(), 'public', 'logo');
      if (fs.existsSync(fallbackDir)) {
        dirToRead = fallbackDir;
      } else {
        return NextResponse.json([]);
      }
    }

    const files = await fs.promises.readdir(dirToRead);
    const imageExtensions = new Set(['.png', '.jpg', '.jpeg', '.svg', '.webp']);
    
    const logos: LogoItem[] = [];
    const seenIds = new Set<string>();

    for (const file of files) {
      const ext = path.extname(file).toLowerCase();
      if (!imageExtensions.has(ext)) continue;

      const baseName = path.basename(file, ext).toLowerCase();
      if (seenIds.has(baseName)) continue;
      seenIds.add(baseName);

      const name = BRAND_NAME_MAP[baseName] || baseName.charAt(0).toUpperCase() + baseName.slice(1);

      logos.push({
        id: baseName,
        name,
        file,
        src: `/logos/${file}`
      });
    }

    // Sort: Jade, DoctorShield, Jaguar, JA Assure first
    const priorityOrder = ['jade', 'doctorshield', 'jaguar', 'ja'];
    logos.sort((a, b) => {
      const idxA = priorityOrder.indexOf(a.id);
      const idxB = priorityOrder.indexOf(b.id);
      if (idxA !== -1 && idxB !== -1) return idxA - idxB;
      if (idxA !== -1) return -1;
      if (idxB !== -1) return 1;
      return a.name.localeCompare(b.name);
    });

    return NextResponse.json(logos);
  } catch (error) {
    console.error('Failed to list logos:', error);
    return NextResponse.json(
      [
        { id: 'jade', name: 'Jade', file: 'Jade.png', src: '/logos/Jade.png' },
        { id: 'doctorshield', name: 'DoctorShield', file: 'doctorshield.png', src: '/logos/doctorshield.png' },
        { id: 'jaguar', name: 'Jaguar Transit', file: 'jaguar.png', src: '/logos/jaguar.png' },
        { id: 'ja', name: 'JA Assure', file: 'ja.png', src: '/logos/ja.png' }
      ]
    );
  }
}
