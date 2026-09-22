'use client';

import React, { useState, useEffect, useRef } from 'react';
import { toast } from 'sonner';
import type { BrandId, CampaignMediaItem, BrandLogoItem } from '@/lib/api/types';
import type { LogoAnchor, WatermarkLogo } from './types';
import { useWatermarkComposer } from './use-watermark-composer';
import { WatermarkCanvas } from './watermark-canvas';
import { applyCampaignWatermark, uploadWatermarkedMedia, getBrandLogos } from '@/lib/api/client';
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
  const [isSaving, setIsSaving] = useState(false);
  const [availableLogos, setAvailableLogos] = useState<BrandLogoItem[]>([
    { name: 'Jade', filename: 'Jade.png', url: '/logos/Jade.png' },
    { name: 'DoctorShield', filename: 'doctorshield.png', url: '/logos/doctorshield.png' },
    { name: 'JA Assure', filename: 'ja.png', url: '/logos/ja.png' },
    { name: 'Jaguar', filename: 'jaguar.png', url: '/logos/jaguar.png' }
  ]);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const {
    logos,
    activeLogoId,
    activeLogo,
    setActiveLogoId,
    addLogo,
    removeLogo,
    updateLogo,
    setAnchorForLogo,
    setPresetLogo,
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

  // Load available local brand logos dynamically from backend
  useEffect(() => {
    getBrandLogos()
      .then((items) => {
        if (items && items.length > 0) {
          setAvailableLogos(items);
        }
      })
      .catch(() => {});
  }, []);

  // Initialize primary logo from brandId
  useEffect(() => {
    const brandMap: Record<string, string> = {
      jade: '/logos/Jade.png',
      doctorshield: '/logos/doctorshield.png',
      jaguar: '/logos/jaguar.png'
    };
    const targetUrl = brandMap[brandId] || '/logos/ja.png';
    const logoName = brandId.charAt(0).toUpperCase() + brandId.slice(1);
    setPresetLogo(targetUrl, logoName);
  }, [brandId, setPresetLogo]);

  // If currently selected media type isn't generated, switch to the one that is
  useEffect(() => {
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
    }
  };

  const handleSelectLogoForActive = (logoItem: BrandLogoItem) => {
    if (!activeLogo) return;
    updateLogo(activeLogo.id, {
      logoPath: logoItem.url,
      name: logoItem.name
    });
  };

  const handleAddNewLogo = (logoItem: BrandLogoItem) => {
    addLogo({
      logoPath: logoItem.url,
      name: logoItem.name,
      anchor: 'top-left',
      scale: 65,
      opacity: 90
    });
    toast.success(`Added secondary watermark: ${logoItem.name}`);
  };

  const handleSaveWatermark = async () => {
    if (!activeMediaItem || !activeMediaUrl) {
      toast.error('No media item available to watermark');
      return;
    }

    setIsSaving(true);
    try {
      const watermarkConfig = {
        logos: logos.map((l) => ({
          id: l.id,
          logo_path: l.logoPath,
          name: l.name,
          anchor: l.anchor,
          scale: l.scale,
          opacity: l.opacity,
          x: l.x,
          y: l.y
        })),
        custom_text: textEnabled ? textConfig.text : null,
        primary_anchor: activeLogo?.anchor || 'bottom-right',
        primary_scale: activeLogo?.scale || 80,
        primary_opacity: activeLogo?.opacity || 90
      };

      if (selectedMediaType === 'image') {
        // Render 1:1 Canvas and get dataURL
        const compResult = await compositeImage(activeMediaUrl);

        const updated = await applyCampaignWatermark(campaignId, {
          media_type: 'image',
          parent_media_id: activeMediaItem.id,
          logo_preset: activeLogo?.logoPath,
          logo_anchor: activeLogo?.anchor || 'bottom-right',
          logo_scale: activeLogo?.scale || 80,
          logo_opacity: activeLogo?.opacity || 90,
          custom_text: textEnabled ? textConfig.text : null,
          image_data: compResult.dataUrl,
          logos: watermarkConfig.logos,
          watermark_config: watermarkConfig
        });

        toast.success('Final watermarked poster saved (final_v1.png)!');
        onWatermarkSaved(updated);
      } else {
        // Video: render frame-by-frame via MediaRecorder and upload blob
        await compositeVideo(activeMediaUrl, 'aura_reel.mp4', async (exportRes) => {
          const formData = new FormData();
          formData.append('file', exportRes.blob, exportRes.fileName);
          formData.append('media_type', 'video');
          formData.append('parent_media_id', activeMediaItem.id);
          formData.append('logo_anchor', activeLogo?.anchor || 'bottom-right');
          formData.append('logo_scale', String(activeLogo?.scale || 80));
          formData.append('logo_opacity', String(activeLogo?.opacity || 90));
          formData.append('watermark_config', JSON.stringify(watermarkConfig));

          const updated = await uploadWatermarkedMedia(campaignId, formData);
          toast.success('Final watermarked video saved (final_v1.mp4)!');
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
            Step 3: Watermark &amp; Multi-Logo Composer
          </Badge>
          <span className='text-xs text-muted-foreground hidden sm:inline'>
            Preserves original AI output and generates verified final watermarked assets.
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
                Drag any logo or text directly on the canvas to reposition freely.
              </CardDescription>
            </CardHeader>
            <CardContent className='pt-0 flex justify-center'>
              <WatermarkCanvas
                mediaType={selectedMediaType}
                mediaSrc={activeMediaUrl}
                logos={logos}
                activeLogoId={activeLogoId}
                onSelectLogo={setActiveLogoId}
                onLogoChange={updateLogo}
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
                  <CardTitle className='text-sm font-bold'>Brand Watermark Configuration</CardTitle>
                  <CardDescription className='text-xs mt-0.5'>
                    Configure multiple brand logos, scales, corner snaps, and text overlays.
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
                    Logos ({logos.length})
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
                  {/* Active Logos Tab Switcher */}
                  <div className='space-y-2'>
                    <div className='flex items-center justify-between'>
                      <Label className='text-xs font-semibold'>Configured Logos</Label>
                      {/* Add Another Logo dropdown / button */}
                      <div className='flex items-center gap-1'>
                        {availableLogos
                          .filter((al) => !logos.some((l) => l.logoPath === al.url))
                          .slice(0, 2)
                          .map((al) => (
                            <Button
                              key={al.url}
                              type='button'
                              size='sm'
                              variant='outline'
                              className='h-6 text-[10px] px-2 gap-1 border-dashed'
                              onClick={() => handleAddNewLogo(al)}
                            >
                              <Icons.add className='size-2.5' />
                              <span>+ Add {al.name}</span>
                            </Button>
                          ))}
                      </div>
                    </div>

                    {/* Logo Selector Pills */}
                    <div className='flex items-center gap-2 flex-wrap'>
                      {logos.map((l, index) => {
                        const isSelected = l.id === activeLogoId;
                        return (
                          <div
                            key={l.id}
                            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs cursor-pointer transition-all ${
                              isSelected
                                ? 'border-primary bg-primary/10 text-primary font-bold shadow-xs'
                                : 'border-border bg-card hover:bg-muted/40 text-foreground'
                            }`}
                            onClick={() => setActiveLogoId(l.id)}
                          >
                            <span>Logo {index + 1}: {l.name || 'Brand'}</span>
                            <span className='text-[10px] font-mono text-muted-foreground'>({l.anchor})</span>
                            {logos.length > 1 && (
                              <button
                                type='button'
                                onClick={(e) => {
                                  e.stopPropagation();
                                  removeLogo(l.id);
                                }}
                                className='hover:text-destructive text-muted-foreground ml-1 p-0.5'
                                title='Remove this logo'
                              >
                                <Icons.close className='size-3' />
                              </button>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* Active Logo Customization Panel */}
                  {activeLogo && (
                    <div className='space-y-4 pt-2 border-t'>
                      {/* Brand Logo Picker */}
                      <div className='space-y-1.5'>
                        <Label className='text-xs font-semibold'>
                          Select Brand Logo for {activeLogo.name || 'Current Logo'}
                        </Label>
                        <div className='grid grid-cols-2 sm:grid-cols-4 gap-2'>
                          {availableLogos.map((preset) => {
                            const isSelected = activeLogo.logoPath === preset.url;
                            return (
                              <button
                                key={preset.url}
                                type='button'
                                onClick={() => handleSelectLogoForActive(preset)}
                                className={`flex items-center gap-2 p-2 rounded-lg border text-left cursor-pointer transition-all ${
                                  isSelected
                                    ? 'border-primary bg-primary/10 ring-1 ring-primary'
                                    : 'border-muted hover:border-foreground/30 bg-card'
                                }`}
                              >
                                {/* eslint-disable-next-line @next/next/no-img-element */}
                                <img
                                  src={preset.url}
                                  alt={preset.name}
                                  className='size-7 object-contain'
                                />
                                <span className='font-bold text-xs truncate'>{preset.name}</span>
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
                            className='w-full border-dashed gap-2 py-2 text-xs'
                          >
                            <Icons.upload className='size-3.5' />
                            <span>Upload Custom Brand Logo File</span>
                          </Button>
                        </div>
                      </div>

                      {/* Corner Snapping */}
                      <div className='space-y-1.5 pt-1'>
                        <Label className='text-xs font-medium'>Placement Snap</Label>
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
                              variant={activeLogo.anchor === corner.id ? 'default' : 'outline'}
                              size='sm'
                              className='text-[11px] h-7 px-1'
                              onClick={() => setAnchorForLogo(activeLogo.id, corner.id as LogoAnchor)}
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
                            <span className='font-mono text-muted-foreground'>{activeLogo.scale}%</span>
                          </div>
                          <Slider
                            min={20}
                            max={180}
                            step={5}
                            value={[activeLogo.scale]}
                            onValueChange={(val) =>
                              updateLogo(activeLogo.id, { scale: Array.isArray(val) ? val[0] : val })
                            }
                          />
                        </div>

                        <div className='space-y-2'>
                          <div className='flex items-center justify-between text-xs'>
                            <Label className='text-xs font-medium'>Watermark Opacity</Label>
                            <span className='font-mono text-muted-foreground'>{activeLogo.opacity}%</span>
                          </div>
                          <Slider
                            min={10}
                            max={100}
                            step={5}
                            value={[activeLogo.opacity]}
                            onValueChange={(val) =>
                              updateLogo(activeLogo.id, { opacity: Array.isArray(val) ? val[0] : val })
                            }
                          />
                        </div>
                      </div>
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
                      ? 'Creates final 1:1 square poster (final_v1.png) with all logos.'
                      : 'Renders branded 9:16 vertical video (final_v1.mp4) with all logos.'}
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
