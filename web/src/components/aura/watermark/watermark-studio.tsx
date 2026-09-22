'use client';

import React, { useState, useRef } from 'react';
import { toast } from 'sonner';
import type { BrandId, CampaignMediaItem } from '@/lib/api/types';
import type { LogoAnchor } from './types';
import { useWatermarkComposer } from './use-watermark-composer';
import { WatermarkCanvas } from './watermark-canvas';
import { applyCampaignWatermark, uploadWatermarkedMedia } from '@/lib/api/client';
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

export const PRESET_LOGOS = [
  {
    id: 'jade',
    name: 'Jade',
    badge: 'Luxury & High Value Risk',
    svg: `data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 170 48" fill="none"><rect width="170" height="48" rx="8" fill="%23061A12" fill-opacity="0.90"/><polygon points="24,10 35,24 24,38 13,24" fill="%2310B981" stroke="%23F59E0B" stroke-width="1.8"/><circle cx="24" cy="24" r="3.5" fill="%23FFFFFF"/><text x="44" y="27" fill="%23F59E0B" font-family="system-ui, sans-serif" font-weight="800" font-size="13" letter-spacing="1.5">JADE</text><text x="44" y="38" fill="%2310B981" font-family="system-ui, sans-serif" font-weight="600" font-size="8.5" letter-spacing="1">SPECIALIST RISK</text></svg>`
  },
  {
    id: 'doctorshield',
    name: 'Doctor Shield',
    badge: 'Clinical Healthcare Care',
    svg: `data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 170 48" fill="none"><rect width="170" height="48" rx="8" fill="%2308263B" fill-opacity="0.90"/><path d="M24 10C24 10 34 12 34 21C34 30 24 37 24 37C24 37 14 30 14 21C14 12 24 10 24 10Z" fill="%230284C7" stroke="%2338BDF8" stroke-width="1.8"/><path d="M24 17V29M18 23H30" stroke="%23FFFFFF" stroke-width="2.2" stroke-linecap="round"/><text x="44" y="27" fill="%23FFFFFF" font-family="system-ui, sans-serif" font-weight="800" font-size="12" letter-spacing="0.8">DOCTOR</text><text x="100" y="27" fill="%2338BDF8" font-family="system-ui, sans-serif" font-weight="800" font-size="12" letter-spacing="0.8">SHIELD</text><text x="44" y="38" fill="%237DD3FC" font-family="system-ui, sans-serif" font-weight="600" font-size="8.5" letter-spacing="1">CLINICAL CARE</text></svg>`
  },
  {
    id: 'jaguar',
    name: 'Jaguar Transit',
    badge: 'Logistics & Secure Transit',
    svg: `data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 170 48" fill="none"><rect width="170" height="48" rx="8" fill="%231E170E" fill-opacity="0.90"/><polygon points="24,10 35,16 35,29 24,37 13,29 13,16" fill="%23D97706" stroke="%23FBBF24" stroke-width="1.8"/><circle cx="24" cy="23.5" r="4" fill="%23FFFFFF"/><text x="44" y="27" fill="%23FBBF24" font-family="system-ui, sans-serif" font-weight="800" font-size="11.5" letter-spacing="0.8">JAGUAR TRANSIT</text><text x="44" y="38" fill="%23FDE68A" font-family="system-ui, sans-serif" font-weight="600" font-size="8.5" letter-spacing="1">SECURE LOGISTICS</text></svg>`
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

interface WatermarkStudioProps {
  campaignId: string;
  brandId: BrandId;
  imageItem?: CampaignMediaItem | null;
  videoItem?: CampaignMediaItem | null;
  onWatermarkSaved: (updatedMedia: CampaignMediaItem) => void;
}

export function WatermarkStudio({
  campaignId,
  brandId,
  imageItem,
  videoItem,
  onWatermarkSaved
}: WatermarkStudioProps) {
  const [selectedMediaType, setSelectedMediaType] = useState<'image' | 'video'>('image');
  const [activeTab, setActiveTab] = useState<'logo' | 'text'>('logo');
  const [selectedPresetId, setSelectedPresetId] = useState<string>(brandId);
  const [isSaving, setIsSaving] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

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
    compositeImage,
    compositeVideo,
    setLogoFile
  } = useWatermarkComposer();

  // Initialize brand preset on mount
  React.useEffect(() => {
    const matching = PRESET_LOGOS.find((p) => p.id === brandId) || PRESET_LOGOS[0];
    setPresetLogo(matching.svg);
    setSelectedPresetId(matching.id);
  }, [brandId, setPresetLogo]);

  // If currently selected media type isn't generated, switch to the one that is
  React.useEffect(() => {
    if (selectedMediaType === 'image' && !imageItem && videoItem) {
      setSelectedMediaType('video');
    } else if (selectedMediaType === 'video' && !videoItem && imageItem) {
      setSelectedMediaType('image');
    }
  }, [imageItem, videoItem, selectedMediaType]);

  const activeMediaItem = selectedMediaType === 'image' ? imageItem : videoItem;

  const resolveMediaUrl = (path?: string | null) => {
    if (!path) return '';
    if (path.startsWith('http://') || path.startsWith('https://') || path.startsWith('data:')) {
      return path;
    }
    const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const cleanPath = path.startsWith('/') ? path : `/${path}`;
    return `${apiBase}${cleanPath}`;
  };

  const activeMediaUrl = resolveMediaUrl(activeMediaItem?.local_path);

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setLogoFile(file);
      setSelectedPresetId('custom');
    }
  };

  const handlePresetSelect = (preset: typeof PRESET_LOGOS[0]) => {
    setPresetLogo(preset.svg);
    setSelectedPresetId(preset.id);
  };

  const handleSaveWatermark = async () => {
    if (!activeMediaItem || !activeMediaUrl) {
      toast.error('No media item available to watermark');
      return;
    }

    setIsSaving(true);
    try {
      if (selectedMediaType === 'image') {
        // Render 1:1 Canvas and get dataURL
        const compResult = await compositeImage(activeMediaUrl);

        const updated = await applyCampaignWatermark(campaignId, {
          media_type: 'image',
          parent_media_id: activeMediaItem.id,
          logo_preset: selectedPresetId,
          logo_anchor: logoConfig.anchor,
          logo_scale: logoConfig.scale,
          logo_opacity: logoConfig.opacity,
          custom_text: textEnabled ? textConfig.text : null,
          image_data: compResult.dataUrl
        });

        toast.success('Final watermarked poster saved (poster_final_v1.png)!');
        onWatermarkSaved(updated);
      } else {
        // Video: render frame-by-frame via MediaRecorder and upload blob
        await compositeVideo(activeMediaUrl, 'aura_reel.mp4', async (exportRes) => {
          const formData = new FormData();
          formData.append('file', exportRes.blob, exportRes.fileName);
          formData.append('media_type', 'video');
          formData.append('parent_media_id', activeMediaItem.id);
          formData.append('logo_anchor', logoConfig.anchor);
          formData.append('logo_scale', String(logoConfig.scale));
          formData.append('logo_opacity', String(logoConfig.opacity));

          const updated = await uploadWatermarkedMedia(campaignId, formData);
          toast.success('Final watermarked video saved (reel_final_v1.mp4)!');
          onWatermarkSaved(updated);
        });
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      toast.error(`Watermarking failed: ${msg}`);
    } finally {
      setIsSaving(false);
    }
  };

  if (!imageItem && !videoItem) {
    return (
      <Card className='border-dashed p-10 text-center'>
        <div className='flex flex-col items-center justify-center space-y-3 py-6'>
          <Icons.sparkles className='size-10 text-muted-foreground stroke-[1.2]' />
          <h3 className='text-base font-bold'>Generate AI Media First</h3>
          <p className='text-xs text-muted-foreground max-w-sm'>
            In Step 2, generate your 1:1 Image Poster or 9:16 Reel Video. Then return here to customize and apply your official brand watermark before submitting to the Review Queue.
          </p>
        </div>
      </Card>
    );
  }

  return (
    <div className='flex flex-col gap-6 w-full'>
      {/* Media Type Switcher: Image Poster vs Video Reel */}
      <div className='flex items-center justify-between border-b pb-4'>
        <div className='flex items-center gap-2'>
          <Badge variant='outline' className='text-xs font-semibold px-2.5 py-1 border-primary/40 bg-primary/10 text-primary'>
            Step 3: Watermark & Brand Marker Studio
          </Badge>
          <span className='text-xs text-muted-foreground hidden sm:inline'>
            Preserves original AI output and generates verified final assets.
          </span>
        </div>

        <div className='flex items-center gap-2 p-1 bg-muted rounded-lg'>
          <Button
            type='button'
            size='sm'
            variant={selectedMediaType === 'image' ? 'default' : 'ghost'}
            className='h-8 text-xs font-semibold px-3 gap-1.5'
            onClick={() => setSelectedMediaType('image')}
            disabled={!imageItem}
          >
            <Icons.media className='size-3.5' />
            <span>Square Poster (1:1)</span>
            {imageItem?.watermarked && (
              <span className='size-2 rounded-full bg-emerald-400 ml-1' title='Watermarked final ready' />
            )}
          </Button>

          <Button
            type='button'
            size='sm'
            variant={selectedMediaType === 'video' ? 'default' : 'ghost'}
            className='h-8 text-xs font-semibold px-3 gap-1.5'
            onClick={() => setSelectedMediaType('video')}
            disabled={!videoItem}
          >
            <Icons.video className='size-3.5' />
            <span>Vertical Reel (9:16)</span>
            {videoItem?.watermarked && (
              <span className='size-2 rounded-full bg-emerald-400 ml-1' title='Watermarked final ready' />
            )}
          </Button>
        </div>
      </div>

      {/* Main 2-Column Layout: Canvas on Left, Controls on Right */}
      <div className='grid grid-cols-1 lg:grid-cols-12 gap-6 items-start'>
        {/* Left Column: Live Interactive Canvas */}
        <div className='lg:col-span-5 flex flex-col gap-3'>
          <Card className='overflow-hidden border-border/80'>
            <CardHeader className='pb-3'>
              <div className='flex items-center justify-between'>
                <CardTitle className='text-sm font-bold'>
                  {selectedMediaType === 'image' ? '1:1 Poster Preview' : '9:16 Vertical Reel Preview'}
                </CardTitle>
                <div className='flex items-center gap-1.5'>
                  {activeMediaItem?.watermarked ? (
                    <Badge variant='outline' className='text-[10px] border-emerald-500/30 bg-emerald-500/10 text-emerald-600 font-semibold'>
                      ✓ Final Watermarked
                    </Badge>
                  ) : (
                    <Badge variant='secondary' className='text-[10px]'>
                      Original AI Generated
                    </Badge>
                  )}
                </div>
              </div>
              <CardDescription className='text-xs'>
                Drag the logo or text directly on the preview to adjust position.
              </CardDescription>
            </CardHeader>
            <CardContent className='pt-0 flex justify-center'>
              <WatermarkCanvas
                mediaType={selectedMediaType}
                mediaSrc={activeMediaUrl}
                logoSrc={logoSrc}
                logoConfig={logoConfig}
                onLogoConfigChange={setLogoConfig}
                textConfig={textConfig}
                onTextConfigChange={setTextConfig}
                textEnabled={textEnabled}
              />
            </CardContent>
          </Card>
        </div>

        {/* Right Column: Customization Controls Card */}
        <div className='lg:col-span-7 flex flex-col gap-4'>
          <Card className='shadow-xs'>
            <CardHeader className='pb-3'>
              <div className='flex items-center justify-between'>
                <div>
                  <CardTitle className='text-sm font-bold'>Brand Marker Configuration</CardTitle>
                  <CardDescription className='text-xs mt-0.5'>
                    Configure logo presets, scale, opacity, and statutory watermark overlays.
                  </CardDescription>
                </div>

                <div className='flex items-center gap-1 p-1 bg-muted rounded-md'>
                  <Button
                    type='button'
                    size='sm'
                    variant={activeTab === 'logo' ? 'default' : 'ghost'}
                    className='h-7 text-xs px-2.5'
                    onClick={() => setActiveTab('logo')}
                  >
                    Brand Logo
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

            <CardContent className='space-y-5 pt-0 text-xs'>
              {activeTab === 'logo' ? (
                <div className='space-y-5'>
                  {/* Presets */}
                  <div className='space-y-2'>
                    <Label className='text-xs font-semibold'>Select Brand Logo Preset</Label>
                    <div className='grid grid-cols-1 sm:grid-cols-3 gap-2.5'>
                      {PRESET_LOGOS.map((preset) => {
                        const isSelected = selectedPresetId === preset.id;
                        return (
                          <button
                            key={preset.id}
                            type='button'
                            onClick={() => handlePresetSelect(preset)}
                            className={`flex flex-col text-left p-2.5 rounded-lg border transition-all cursor-pointer ${
                              isSelected
                                ? 'border-primary bg-primary/10 ring-1 ring-primary'
                                : 'border-muted hover:border-foreground/30 bg-card'
                            }`}
                          >
                            <span className='font-bold text-xs'>{preset.name}</span>
                            <span className='text-[10px] text-muted-foreground line-clamp-1 mt-0.5'>{preset.badge}</span>
                          </button>
                        );
                      })}
                    </div>

                    {/* Custom Upload */}
                    <div className='pt-1'>
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
                        className='w-full border-dashed gap-2 py-2.5 text-xs'
                      >
                        <Icons.upload className='size-3.5' />
                        <span>Upload Custom PNG / SVG Brand Logo</span>
                      </Button>
                    </div>
                  </div>

                  {/* Placement Snap & Sliders */}
                  <div className='space-y-4 pt-2 border-t'>
                    <div className='space-y-1.5'>
                      <Label className='text-xs font-medium'>Corner Placement Snap</Label>
                      <div className='grid grid-cols-5 gap-1.5'>
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
                            className='text-[11px] h-7 px-1'
                            onClick={() => setAnchor(corner.id as LogoAnchor)}
                          >
                            {corner.label}
                          </Button>
                        ))}
                      </div>
                    </div>

                    {/* Scale & Opacity */}
                    <div className='grid grid-cols-1 sm:grid-cols-2 gap-4 pt-1'>
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

                      <div className='space-y-2'>
                        <div className='flex items-center justify-between text-xs'>
                          <Label className='text-xs font-medium'>Watermark Opacity</Label>
                          <span className='font-mono text-muted-foreground'>{logoConfig.opacity}%</span>
                        </div>
                        <Slider
                          min={10}
                          max={100}
                          step={5}
                          value={[logoConfig.opacity]}
                          onValueChange={(val) =>
                            setLogoConfig((p) => ({ ...p, opacity: Array.isArray(val) ? val[0] : val }))
                          }
                        />
                      </div>
                    </div>
                  </div>
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
                      <Icons.sparkles className='size-3' />
                      {textEnabled ? 'Enabled' : 'Disabled'}
                    </Button>
                  </div>

                  {textEnabled ? (
                    <div className='space-y-4 pt-2'>
                      <div className='space-y-1.5'>
                        <Label className='text-xs font-medium'>Overlay Tagline</Label>
                        <Input
                          value={textConfig.text}
                          onChange={(e) => setTextConfig((p) => ({ ...p, text: e.target.value }))}
                          placeholder='e.g. Underwritten by JA Assure • Specialist Protection'
                          className='text-xs'
                        />
                      </div>

                      <div className='grid grid-cols-1 sm:grid-cols-2 gap-4'>
                        <div className='space-y-2'>
                          <div className='flex items-center justify-between text-xs'>
                            <Label className='text-xs font-medium'>Font Size</Label>
                            <span className='font-mono text-muted-foreground'>{textConfig.fontSize}px</span>
                          </div>
                          <Slider
                            min={12}
                            max={42}
                            step={1}
                            value={[textConfig.fontSize]}
                            onValueChange={(val) =>
                              setTextConfig((p) => ({ ...p, fontSize: Array.isArray(val) ? val[0] : val }))
                            }
                          />
                        </div>

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
                              onClick={() => setTextConfig((p) => ({ ...p, color }))}
                              style={{ backgroundColor: color }}
                              className={`size-6 rounded-full border border-black/20 shadow-xs transition-transform ${
                                textConfig.color === color
                                  ? 'ring-2 ring-primary ring-offset-2 scale-110'
                                  : 'hover:scale-105'
                              }`}
                            />
                          ))}
                          <input
                            type='color'
                            value={textConfig.color}
                            onChange={(e) => setTextConfig((p) => ({ ...p, color: e.target.value }))}
                            className='size-7 rounded cursor-pointer border border-input bg-transparent p-0 ml-1'
                          />
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className='p-4 text-center rounded-lg bg-muted/40 text-muted-foreground text-xs'>
                      Click &quot;Disabled&quot; above to enable custom text / tagline overlay.
                    </div>
                  )}
                </div>
              )}
            </CardContent>

            <CardFooter className='border-t bg-muted/20 px-6 py-4 flex flex-col sm:flex-row items-center justify-between gap-4'>
              <div className='w-full sm:w-auto flex-1'>
                {isExporting ? (
                  <div className='space-y-1.5 w-full'>
                    <div className='flex items-center justify-between text-xs'>
                      <span className='font-medium text-primary'>Compositing branded video frame-by-frame...</span>
                      <span className='font-mono font-semibold'>{exportProgress}%</span>
                    </div>
                    <Progress value={exportProgress} className='h-1.5' />
                  </div>
                ) : (
                  <p className='text-xs text-muted-foreground'>
                    {selectedMediaType === 'image'
                      ? 'Creates final 1:1 square poster (poster_final_v1.png).'
                      : 'Renders branded 9:16 vertical video (reel_final_v1.mp4).'}
                  </p>
                )}
              </div>

              <Button
                type='button'
                size='default'
                onClick={handleSaveWatermark}
                disabled={isSaving || isExporting || !activeMediaUrl}
                className='w-full sm:w-auto font-bold gap-2 min-w-[220px]'
              >
                {isSaving || isExporting ? (
                  <>
                    <Icons.spinner className='size-4 animate-spin' />
                    <span>Applying Watermark...</span>
                  </>
                ) : (
                  <>
                    <Icons.checks className='size-4' />
                    <span>Apply &amp; Save Final Watermark</span>
                  </>
                )}
              </Button>
            </CardFooter>
          </Card>
        </div>
      </div>
    </div>
  );
}
