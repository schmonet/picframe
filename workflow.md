```mermaid
graph TD
    subgraph Legende
        direction LR
        Decision((Entscheidung))
        Action[Aktion/Zustand]
        ConfigValue>Konfigurationswert]
    end

        Start((Start)) --> MediaType{Medientyp?};

        MediaType -->|Video| VideoLogic;
        MediaType -->|Bild| CheckCrop;

        subgraph VideoAblauf ["Video Slideshow (ffmpeg)"]
            VideoLogic["Video erkannt"] --> ExtractFrames["Frames extrahieren (ffmpeg)"];
            ExtractFrames --> LoopFrames["Schleife über Frames"];
            LoopFrames --> BlendFrames["Überblendung (Cross-Fade)"];
            BlendFrames --> ShowFrame["Frame anzeigen (statisch)"];
            ShowFrame --> NextFrame{Nächster Frame?};
            NextFrame -->|Ja| LoopFrames;
            NextFrame -->|Nein| EndVideo["Ende"];
        end

        CheckCrop{crop_to_aspect_ratio gesetzt?};
        CheckCrop -->|Ja| DoCrop["Bild auf Seitenverhältnis zuschneiden"];
        CheckCrop -->|Nein| IsKenBurns;
        DoCrop --> IsKenBurns;

        subgraph KenBurnsAblauf ["Ken Burns Logic (Bilder)"]
            IsKenBurns{kenburns: true?}
            IsKenBurns -->|Nein| CheckFit{fit: true?};
            
            CheckFit -->|Ja| StaticFit["Bild einpassen (schwarze Ränder)"];
            CheckFit -->|Nein| StaticCrop["Bild füllen (Zuschnitt)"];

            IsKenBurns -->|Ja| CheckAspectRatio{Seitenverhältnis?};

            CheckAspectRatio -->|"Hochformat (AR < Viewport)"| PortraitLogic;
            CheckAspectRatio -->|"Panorama (AR > Screen)"| PanoramaLogic;
            CheckAspectRatio -->|"Querformat (Sonst)"| LandscapeLogic;

            subgraph PortraitLogik ["Hochformat: Vertikaler Scroll"]
                PortraitLogic --> PortraitRandomPan{kenburns_random_pan: true?};
                PortraitRandomPan -->|Ja| PortraitWobble["1. Leichter Zoom für Wobble-Effekt<br>2. Zufälliger horizontaler Pan<br>max. Stärke: kenburns_portrait_wobble_pct"];
                PortraitRandomPan -->|Nein| PortraitNoWobble["Kein horizontaler Pan"];
                
                PortraitWobble --> PortraitScrollDir;
                PortraitNoWobble --> PortraitScrollDir;

                PortraitScrollDir{kenburns_portrait_scroll_direction?};
                PortraitScrollDir -->|'random'| PortraitRandomScroll["Richtung zufällig (up/down)"];
                PortraitScrollDir -->|'up'| PortraitScrollUp["Scrollt von unten nach oben"];
                PortraitScrollDir -->|'down'| PortraitScrollDown["Scrollt von oben nach unten"];

                PortraitRandomScroll --> ApplyTransform;
                PortraitScrollUp --> ApplyTransform;
                PortraitScrollDown --> ApplyTransform;
            end

            subgraph PanoramaLogik ["Panorama: Horizontaler Scroll"]
                PanoramaLogic --> PanoramaZoomDir{kenburns_panorama_zoom_direction?};
                PanoramaZoomDir -->|'random'| PanoramaRandomZoom["Zoom-Richtung zufällig (in/out)"];
                PanoramaZoomDir -->|'in'| PanoramaZoomIn["Zoomt hinein"];
                PanoramaZoomDir -->|'out'| PanoramaZoomOut["Zoomt heraus"];

                PanoramaRandomZoom --> PanoramaZoomPct;
                PanoramaZoomIn --> PanoramaZoomPct;
                PanoramaZoomOut --> PanoramaZoomPct;

                PanoramaZoomPct["Zoom-Stärke: kenburns_panorama_zoom_pct"] --> PanoramaScrollDir;

                PanoramaScrollDir{kenburns_panorama_scroll_direction?};
                PanoramaScrollDir -->|'random'| PanoramaRandomScrollH["Richtung zufällig (left/right)"];
                PanoramaScrollDir -->|'left'| PanoramaScrollLeft["Scrollt nach links"];
                PanoramaScrollDir -->|'right'| PanoramaScrollRight["Scrollt nach rechts"];

                PanoramaRandomScrollH --> PanoramaWobbleCheck;
                PanoramaScrollLeft --> PanoramaWobbleCheck;
                PanoramaScrollRight --> PanoramaWobbleCheck;

                PanoramaWobbleCheck{kenburns_random_pan: true?};
                PanoramaWobbleCheck -->|Ja| PanoramaWobble["Zufälliger vertikaler Pan (Wobble)"];
                PanoramaWobbleCheck -->|Nein| PanoramaNoWobble["Kein vertikaler Pan"];
                
                PanoramaWobble --> ApplyTransform;
                PanoramaNoWobble --> ApplyTransform;
            end

            subgraph LandscapeLogik ["Querformat: Zoom"]
                LandscapeLogic --> LandscapeZoomDir{kenburns_landscape_zoom_direction?};
                LandscapeZoomDir -->|'random'| LandscapeRandomZoom["Zoom-Richtung zufällig (in/out)"];
                LandscapeZoomDir -->|'in'| LandscapeZoomIn["Zoomt hinein (100% -> 1xx%)"];
                LandscapeZoomDir -->|'out'| LandscapeZoomOut["Zoomt heraus (1xx% -> 100%)"];

                LandscapeRandomZoom --> LandscapeZoomPct;
                LandscapeZoomIn --> LandscapeZoomPct;
                LandscapeZoomOut --> LandscapeZoomPct;

                LandscapeZoomPct["Zoom-Stärke zufällig<br>max. Stärke: kenburns_landscape_zoom_pct"];
                LandscapeZoomPct --> LandscapeRandomPan{kenburns_random_pan: true?};
                LandscapeRandomPan -->|Ja| LandscapeWobble["Zufälliger horizontaler & vertikaler Pan<br>max. Stärke: kenburns_landscape_wobble_pct"];
                LandscapeRandomPan -->|Nein| LandscapeNoWobble["Zentrierter Zoom ohne Pan"];
                
                LandscapeWobble --> ApplyTransform;
                LandscapeNoWobble --> ApplyTransform;
            end
            
            ApplyTransform["Transformation wird berechnet & angewendet"];
        end
