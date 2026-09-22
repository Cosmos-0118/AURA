'use client';

import React, { useState } from 'react';
import type { VideoAspectRatio, VideoGenerateResponse } from '@/lib/api/types';
import type { LogoAnchor } from '../types/brand-types';
import { useBrandComposer } from '../hooks/use-brand-composer';
import { BrandCanvas } from './brand-canvas';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  CardFooter
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Slider } from '@/components/ui/slider';
import { Progress } from '@/components/ui/progress';
import { Icons } from '@/components/icons';
import { IconDownload, IconSparkles, IconUpload, IconTrash } from '@tabler/icons-react';

// Pre-packaged SVGs for instantaneous 1-click branding
const PRESET_LOGOS = [
  {
    id: 'jade',
    name: 'Jade Luxury',
    badge: 'Jewellery',
    svg: `data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 160 48" fill="none"><rect width="160" height="48" rx="8" fill="%23041F15" fill-opacity="0.85"/><path d="M24 12L34 24L24 36L14 24L24 12Z" fill="%2310B981" stroke="%2334D399" stroke-width="2"/><circle cx="24" cy="24" r="3" fill="%23FFFFFF"/><text x="44" y="29" fill="%23FFFFFF" font-family="system-ui, sans-serif" font-weight="700" font-size="14" letter-spacing="1.5">JADE</text><text x="92" y="29" fill="%2310B981" font-family="system-ui, sans-serif" font-weight="500" font-size="11">ASSURE</text></svg>`
  },
  {
    id: 'doctorshield',
    name: 'DoctorShield',
    badge: 'Clinics',
    svg: `data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 160 48" fill="none"><rect width="160" height="48" rx="8" fill="%23082F49" fill-opacity="0.85"/><path d="M24 12C24 12 33 14 33 21C33 29 24 35 24 35C24 35 15 29 15 21C15 14 24 12 24 12Z" fill="%230284C7" stroke="%2338BDF8" stroke-width="2"/><path d="M24 18V28M19 23H29" stroke="%23FFFFFF" stroke-width="2.5" stroke-linecap="round"/><text x="42" y="29" fill="%23FFFFFF" font-family="system-ui, sans-serif" font-weight="700" font-size="12" letter-spacing="0.5">DOCTOR</text><text x="96" y="29" fill="%2338BDF8" font-family="system-ui, sans-serif" font-weight="700" font-size="12">SHIELD</text></svg>`
  },
  {
    id: 'jaguar',
    name: 'Jaguar Transit',
    badge: 'Logistics',
    svg: `data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 160 48" fill="none"><rect width="160" height="48" rx="8" fill="%23271A0C" fill-opacity="0.85"/><polygon points="24,12 34,18 34,30 24,36 14,30 14,18" fill="%23D97706" stroke="%23FBBF24" stroke-width="2"/><path d="M19 24L23 28L29 20" stroke="%23FFFFFF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><text x="44" y="29" fill="%23FFFFFF" font-family="system-ui, sans-serif" font-weight="700" font-size="13" letter-spacing="1">JAGUAR</text><text x="105" y="29" fill="%23FBBF24" font-family="system-ui, sans-serif" font-weight="600" font-size="11">SECURE</text></svg>`
  }
];

const COLOR_SWATCHES = [
  '#ffffff',
  '#fbbf24',
  '#34d399',
  '#38bdf8',
  '#f43f5e',
  '#a855f7',
  '#000000'
];

interface BrandMarkerStudioProps {
  videoResult: VideoGenerateResponse | null;
  aspectRatio: VideoAspectRatio;
}

export function BrandMarkerStudio({ videoResult, aspectRatio }: BrandMarkerStudioProps) {
  const {
    logoSrc,
    setPresetLogo,
    logoConfig,
    setLogoConfig,
    setAnchor,
    textConfig,
    setTextConfig,
    textEnabled,
    setTextEnabled,
    isExporting,
    exportProgress,
    compositeAndExport,
    setLogoFile
  } = useBrandComposer();

  const [activeTab, setActiveTab] = useState<'logo' | 'text'>('logo');
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  const videoUrl = videoResult?.video?.url;

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setLogoFile(file);
    }
  };

  const handleExport = () => {
    if (!videoUrl) return;
    compositeAndExport(videoUrl, videoResult?.video?.file_name || 'aura_video.mp4');
  };

  const clearLogo = () => {
    setPresetLogo('');
  };

  if (!videoUrl) {
    return (
      <Card className='p-8 text-center border-dashed'>
        <div className='flex flex-col items-center justify-center space-y-3 py-6'>
          <Icons.video className='size-10 text-muted-foreground stroke-[1.2]' />
          <h3 className='text-base font-semibold'>Generate a Video First</h3>
          <p className='text-xs text-muted-foreground max-w-sm'>
            Create or generate a video reel in the studio before applying company brand markers and
            custom overlays.
          </p>
        </div>
      </Card>
    );
  }

  return (
    <div className='space-y-6'>
      {/* Live Preview Canvas and Watermark Position */}
      <Card className='overflow-hidden border-border/80'>
        <CardHeader className='pb-3'>
          <div className='flex items-center justify-between'>
            <div className='flex items-center gap-2'>
              <CardTitle className='text-base font-semibold'>Branded Video Preview</CardTitle>
              <Badge
                variant='outline'
                className='border-primary/40 bg-primary/10 text-primary text-[11px]'
              >
                Interactive Watermark
              </Badge>
            </div>
            {logoSrc && (
              <Badge
                variant='secondary'
                className='text-[10px] text-emerald-600 dark:text-emerald-400'
              >
                Logo Active
              </Badge>
            )}
          </div>
          <CardDescription>
            Position your company badge and custom elements directly on the video reel.
          </CardDescription>
        </CardHeader>
        <CardContent className='pt-0'>
          <BrandCanvas
            videoSrc={videoUrl}
            logoSrc={logoSrc}
            logoConfig={logoConfig}
            onLogoConfigChange={setLogoConfig}
            textConfig={textConfig}
            onTextConfigChange={setTextConfig}
            textEnabled={textEnabled}
            aspectRatio={aspectRatio}
          />
        </CardContent>
      </Card>

      {/* Brand Customization Controls Card */}
      <Card>
        <CardHeader className='pb-3'>
          <div className='flex items-center justify-between'>
            <CardTitle className='text-base font-semibold'>Brand Marker Configuration</CardTitle>
            <div className='flex items-center gap-1.5 p-1 bg-muted rounded-md'>
              <Button
                type='button'
                size='sm'
                variant={activeTab === 'logo' ? 'default' : 'ghost'}
                className='h-7 text-xs px-2.5'
                onClick={() => setActiveTab('logo')}
              >
                Company Logo
              </Button>
              <Button
                type='button'
                size='sm'
                variant={activeTab === 'text' ? 'default' : 'ghost'}
                className='h-7 text-xs px-2.5'
                onClick={() => setActiveTab('text')}
              >
                Custom Text
              </Button>
            </div>
          </div>
        </CardHeader>

        <CardContent className='space-y-5 pt-0'>
          {activeTab === 'logo' ? (
            <div className='space-y-5'>
              {/* Preset Logos & Upload */}
              <div className='space-y-2.5'>
                <div className='flex items-center justify-between'>
                  <Label className='text-xs font-semibold'>Company Logo Presets</Label>
                  {logoSrc && (
                    <button
                      type='button'
                      onClick={clearLogo}
                      className='text-[11px] text-destructive hover:underline flex items-center gap-1'
                    >
                      <IconTrash className='size-3' />
                      Remove Logo
                    </button>
                  )}
                </div>

                <div className='grid grid-cols-1 sm:grid-cols-3 gap-2.5'>
                  {PRESET_LOGOS.map((preset) => (
                    <Button
                      key={preset.id}
                      type='button'
                      variant='outline'
                      size='sm'
                      onClick={() => setPresetLogo(preset.svg)}
                      className={`h-auto flex-col items-start p-2.5 text-left transition-all ${
                        logoSrc === preset.svg
                          ? 'border-primary ring-1 ring-primary'
                          : 'hover:border-primary/50'
                      }`}
                    >
                      <span className='font-medium text-xs'>{preset.name}</span>
                      <span className='text-[10px] text-muted-foreground'>{preset.badge}</span>
                    </Button>
                  ))}
                </div>

                {/* Custom File Upload Area */}
                <div className='pt-2'>
                  <input
                    ref={fileInputRef}
                    type='file'
                    accept='image/png,image/svg+xml,image/webp,image/jpeg'
                    onChange={handleFileUpload}
                    className='hidden'
                  />
                  <Button
                    type='button'
                    variant='outline'
                    size='sm'
                    onClick={() => fileInputRef.current?.click()}
                    className='w-full border-dashed gap-2 py-3 text-xs'
                  >
                    <IconUpload className='size-3.5' />
                    <span>Upload Custom PNG / SVG Brand Logo</span>
                  </Button>
                </div>
              </div>

              {/* Position Snap & Dimensions */}
              {logoSrc ? (
                <div className='space-y-4 pt-2 border-t'>
                  {/* Corner Snap Anchors */}
                  <div className='space-y-1.5'>
                    <Label className='text-xs font-medium'>Corner Placement Snap</Label>
                    <div className='grid grid-cols-5 gap-2'>
                      {(
                        [
                          { id: 'top-left', label: 'Top Left' },
                          { id: 'top-right', label: 'Top Right' },
                          { id: 'center', label: 'Center' },
                          { id: 'bottom-left', label: 'Bottom Left' },
                          { id: 'bottom-right', label: 'Bottom Right' }
                        ] as const
                      ).map((corner) => (
                        <Button
                          key={corner.id}
                          type='button'
                          variant={logoConfig.anchor === corner.id ? 'default' : 'outline'}
                          size='sm'
                          className='text-[11px] h-8 px-1.5'
                          onClick={() => setAnchor(corner.id as LogoAnchor)}
                        >
                          {corner.label}
                        </Button>
                      ))}
                    </div>
                  </div>

                  {/* Scale & Opacity Sliders */}
                  <div className='grid grid-cols-1 sm:grid-cols-2 gap-4 pt-1'>
                    {/* Scale */}
                    <div className='space-y-2'>
                      <div className='flex items-center justify-between text-xs'>
                        <Label className='text-xs font-medium'>Logo Scale</Label>
                        <span className='font-mono text-muted-foreground'>{logoConfig.scale}%</span>
                      </div>
                      <Slider
                        min={20}
                        max={180}
                        step={5}
                        value={[logoConfig.scale]}
                        onValueChange={(val) =>
                          setLogoConfig((p) => ({ ...p, scale: Array.isArray(val) ? val[0] : val }))
                        }
                      />
                    </div>

                    {/* Opacity */}
                    <div className='space-y-2'>
                      <div className='flex items-center justify-between text-xs'>
                        <Label className='text-xs font-medium'>Watermark Opacity</Label>
                        <span className='font-mono text-muted-foreground'>
                          {logoConfig.opacity}%
                        </span>
                      </div>
                      <Slider
                        min={10}
                        max={100}
                        step={5}
                        value={[logoConfig.opacity]}
                        onValueChange={(val) =>
                          setLogoConfig((p) => ({
                            ...p,
                            opacity: Array.isArray(val) ? val[0] : val
                          }))
                        }
                      />
                    </div>
                  </div>
                </div>
              ) : (
                <div className='p-4 text-center rounded-lg bg-muted/40 text-muted-foreground text-xs'>
                  Select a preset logo above or upload your own to unlock size, position, and
                  opacity controls.
                </div>
              )}
            </div>
          ) : (
            /* Custom Text Overlay Options */
            <div className='space-y-4'>
              <div className='flex items-center justify-between'>
                <Label className='text-xs font-semibold'>Custom Text / Tagline Overlay</Label>
                <Button
                  type='button'
                  variant={textEnabled ? 'default' : 'outline'}
                  size='sm'
                  className='h-7 text-xs gap-1.5'
                  onClick={() => setTextEnabled(!textEnabled)}
                >
                  <IconSparkles className='size-3' />
                  {textEnabled ? 'Enabled' : 'Disabled'}
                </Button>
              </div>

              {textEnabled ? (
                <div className='space-y-4 pt-2'>
                  <div className='space-y-1.5'>
                    <Label className='text-xs font-medium'>Overlay Message</Label>
                    <Input
                      value={textConfig.text}
                      onChange={(e) => setTextConfig((p) => ({ ...p, text: e.target.value }))}
                      placeholder='e.g. Insured by JA Assure • Specialist Protection'
                      className='text-xs'
                    />
                  </div>

                  <div className='grid grid-cols-1 sm:grid-cols-2 gap-4'>
                    {/* Font Size */}
                    <div className='space-y-2'>
                      <div className='flex items-center justify-between text-xs'>
                        <Label className='text-xs font-medium'>Font Size</Label>
                        <span className='font-mono text-muted-foreground'>
                          {textConfig.fontSize}px
                        </span>
                      </div>
                      <Slider
                        min={12}
                        max={42}
                        step={1}
                        value={[textConfig.fontSize]}
                        onValueChange={(val) =>
                          setTextConfig((p) => ({
                            ...p,
                            fontSize: Array.isArray(val) ? val[0] : val
                          }))
                        }
                      />
                    </div>

                    {/* Styling Controls */}
                    <div className='space-y-2'>
                      <Label className='text-xs font-medium'>Typography Style</Label>
                      <div className='flex items-center gap-2'>
                        <Button
                          type='button'
                          size='sm'
                          variant={textConfig.bold ? 'default' : 'outline'}
                          className='h-8 px-3 text-xs'
                          onClick={() => setTextConfig((p) => ({ ...p, bold: !p.bold }))}
                        >
                          Bold
                        </Button>
                        <Button
                          type='button'
                          size='sm'
                          variant={textConfig.italic ? 'default' : 'outline'}
                          className='h-8 px-3 text-xs'
                          onClick={() => setTextConfig((p) => ({ ...p, italic: !p.italic }))}
                        >
                          Italic
                        </Button>
                      </div>
                    </div>
                  </div>

                  {/* Color Palette */}
                  <div className='space-y-2 pt-1'>
                    <Label className='text-xs font-medium'>Text Color</Label>
                    <div className='flex items-center gap-2'>
                      {COLOR_SWATCHES.map((color) => (
                        <button
                          key={color}
                          type='button'
                          aria-label={`Select color ${color}`}
                          onClick={() => setTextConfig((p) => ({ ...p, color }))}
                          style={{ backgroundColor: color }}
                          className={`size-6 rounded-full border border-black/20 shadow-xs transition-transform ${
                            textConfig.color === color
                              ? 'ring-2 ring-primary ring-offset-2 scale-110'
                              : 'hover:scale-105'
                          }`}
                          title={color}
                        />
                      ))}
                      <input
                        type='color'
                        value={textConfig.color}
                        onChange={(e) => setTextConfig((p) => ({ ...p, color: e.target.value }))}
                        className='size-7 rounded cursor-pointer border border-input bg-transparent p-0 ml-1'
                        title='Custom Color'
                      />
                    </div>
                  </div>
                </div>
              ) : (
                <div className='p-4 text-center rounded-lg bg-muted/40 text-muted-foreground text-xs'>
                  Click "Disabled" above to enable custom text/tagline overlay on the video.
                </div>
              )}
            </div>
          )}
        </CardContent>

        {/* Card Footer with Export Trigger */}
        <CardFooter className='border-t bg-muted/20 px-6 py-4 flex flex-col sm:flex-row items-center justify-between gap-4'>
          <div className='w-full sm:w-auto flex-1'>
            {isExporting ? (
              <div className='space-y-1.5 w-full'>
                <div className='flex items-center justify-between text-xs'>
                  <span className='font-medium text-primary'>
                    Compositing branded video frame-by-frame...
                  </span>
                  <span className='font-mono font-semibold'>{exportProgress}%</span>
                </div>
                <Progress value={exportProgress} className='h-1.5' />
              </div>
            ) : (
              <p className='text-xs text-muted-foreground'>
                Renders logo & text overlays frame-accurate directly in browser.
              </p>
            )}
          </div>

          <Button
            type='button'
            size='lg'
            onClick={handleExport}
            disabled={isExporting || !videoUrl}
            className='w-full sm:w-auto font-semibold gap-2 min-w-[200px]'
          >
            {isExporting ? (
              <>
                <Icons.spinner className='size-4 animate-spin' />
                Exporting ({exportProgress}%)...
              </>
            ) : (
              <>
                <IconDownload className='size-4' />
                Export Branded Video
              </>
            )}
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
}
