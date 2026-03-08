```mermaid
graph TD
    subgraph Legende
        direction LR
        Decision((Decision))
        Action[Action/State]
        ConfigValue>Configuration Value]
    end

    Start((Start)) --> MediaType{Media Type?};

    MediaType -->|Video| VideoLogic;
    MediaType -->|Image| PreProcess["Image Pre-Processing (blocking)"];

    subgraph PreProcessing ["Image Pre-Processing"]
        style PreProcessing fill:#e0f7fa
        PreProcess --> LoadImage["Load & Orient Image (PIL)"];
        LoadImage --> SmartDownscale{"Image > 125% Viewport?"};
        SmartDownscale --> |Yes| Downscale["Downsizing (im.thumbnail)"];
        SmartDownscale --> |No| CheckCrop;
        Downscale --> CheckCrop;
        CheckCrop{crop_to_aspect_ratio set?};
        CheckCrop -->|Yes| DoCrop["Crop image to aspect ratio"];
        CheckCrop -->|No| GpuUpload;
        DoCrop --> GpuUpload;
        GpuUpload["Create Texture & Upload to GPU<br>(load_opengl)"];
    end

    GpuUpload --> StartAnimation["Start Animation<br>(Freeze ended)"];
    StartAnimation --> IsKenBurns;

    subgraph VideoAblauf ["Video Slideshow (ffmpeg)"]
        style VideoAblauf fill:#e8f5e9
        VideoLogic["Video detected"] --> ExtractFrames["Extract Frames (ffmpeg)"];
        ExtractFrames --> LoopFrames["Loop over Frames"];
        LoopFrames --> BlendFrames["Cross-Fade"];
    end

    subgraph KenBurnsAblauf ["Ken Burns Logic (Images)"]
        style KenBurnsAblauf fill:#fffde7
        IsKenBurns{kenburns: true?}
        IsKenBurns -->|No| CheckFit{fit: true?};
        
        CheckFit -->|Yes| StaticFit["Fit Image (black borders)"];
        CheckFit -->|No| StaticCrop["Fill Image (crop)"];

        IsKenBurns -->|Yes| CheckAspectRatio{Aspect Ratio?};

        CheckAspectRatio -->|"Portrait (AR < Viewport)"| PortraitLogic;
        CheckAspectRatio -->|"Panorama (AR > Screen)"| PanoramaLogic;
        CheckAspectRatio -->|"Landscape (Other)"| LandscapeLogic;

        subgraph PortraitLogik ["Portrait: Vertical Scroll"]
            style PortraitLogik fill:#fff3e0
            PortraitLogic --> PortraitRandomPan{kenburns_random_pan: true?};
            PortraitRandomPan -->|Yes| PortraitWobble["1. Slight zoom for wobble effect<br>2. Random horizontal pan<br>max. strength: kenburns_portrait_wobble_pct"];
            PortraitRandomPan -->|No| PortraitNoWobble["No horizontal pan"];
            
            PortraitWobble --> PortraitScrollDir;
            PortraitNoWobble --> PortraitScrollDir;

            PortraitScrollDir{kenburns_portrait_scroll_direction?};
            PortraitScrollDir -->|'random'| PortraitRandomScroll["Direction random (up/down)"];
            PortraitScrollDir -->|'up'| PortraitScrollUp["Scrolls from bottom to top"];
            PortraitScrollDir -->|'down'| PortraitScrollDown["Scrolls from top to bottom"];

            PortraitRandomScroll --> ApplyTransform;
            PortraitScrollUp --> ApplyTransform;
            PortraitScrollDown --> ApplyTransform;
        end

        subgraph PanoramaLogik ["Panorama: Horizontal Scroll"]
            style PanoramaLogik fill:#f3e5f5
            PanoramaLogic --> PanoramaZoomDir{kenburns_panorama_zoom_direction?};
            PanoramaZoomDir -->|'random'| PanoramaRandomZoom["Zoom direction random (in/out)"];
            PanoramaZoomDir -->|'in'| PanoramaZoomIn["Zooms in"];
            PanoramaZoomDir -->|'out'| PanoramaZoomOut["Zooms out"];

            PanoramaRandomZoom --> PanoramaZoomPct;
            PanoramaZoomIn --> PanoramaZoomPct;
            PanoramaZoomOut --> PanoramaZoomPct;

            PanoramaZoomPct["Zoom strength: kenburns_panorama_zoom_pct"] --> PanoramaScrollDir;

            PanoramaScrollDir{kenburns_panorama_scroll_direction?};
            PanoramaScrollDir -->|'random'| PanoramaRandomScrollH["Direction random (left/right)"];
            PanoramaScrollDir -->|'left'| PanoramaScrollLeft["Scrolls to the left"];
            PanoramaScrollDir -->|'right'| PanoramaScrollRight["Scrolls to the right"];

            PanoramaRandomScrollH --> PanoramaWobbleCheck;
            PanoramaScrollLeft --> PanoramaWobbleCheck;
            PanoramaScrollRight --> PanoramaWobbleCheck;

            PanoramaWobbleCheck{kenburns_random_pan: true?};
            PanoramaWobbleCheck -->|Yes| PanoramaWobble["Random vertical pan (Wobble)"];
            PanoramaWobbleCheck -->|No| PanoramaNoWobble["No vertical pan"];
            
            PanoramaWobble --> ApplyTransform;
            PanoramaNoWobble --> ApplyTransform;
        end

        subgraph LandscapeLogik ["Landscape: Zoom"]
            style LandscapeLogik fill:#fce4ec
            LandscapeLogic --> LandscapeZoomDir{kenburns_zoom_direction?};
            LandscapeZoomDir -->|'random'| LandscapeRandomZoom["Zoom direction random (in/out)"];
            LandscapeZoomDir -->|'in'| LandscapeZoomIn["Zooms in (100% -> 1xx%)"];
            LandscapeZoomDir -->|'out'| LandscapeZoomOut["Zooms out (1xx% -> 100%)"];

            LandscapeRandomZoom --> LandscapeZoomPct;
            LandscapeZoomIn --> LandscapeZoomPct;
            LandscapeZoomOut --> LandscapeZoomPct;

            LandscapeZoomPct["Zoom strength random<br>max. strength: kenburns_landscape_zoom_pct"];
            LandscapeZoomPct --> LandscapeRandomPan{kenburns_random_pan: true?};
            LandscapeRandomPan -->|Yes| LandscapeWobble["Random horizontal & vertical pan<br>max. strength: kenburns_landscape_wobble_pct"];
            LandscapeRandomPan -->|No| LandscapeNoWobble["Centered zoom without pan"];
            
            LandscapeWobble --> ApplyTransform;
            LandscapeNoWobble --> ApplyTransform;
        end
        
        ApplyTransform["Transformation is calculated & applied"];
    end
