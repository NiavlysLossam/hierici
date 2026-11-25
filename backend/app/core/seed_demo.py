import asyncio
import uuid
from pathlib import Path
from datetime import datetime, timezone
from PIL import Image, ImageDraw
from sqlalchemy import select
from geoalchemy2.shape import from_shape
from shapely.geometry import Point

from app.core.database import AsyncSessionLocal
from app.models.territory import Territory
from app.models.user import User
from app.models.photo import Photo, PhotoStatus
from app.models.storymap import Storymap, StorymapStep, StorymapStatus
from app.config import settings


def generate_vintage_image(output_path: Path, title: str, subtitle: str, color=(75, 60, 45)):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (1200, 800), color=color)
    draw = ImageDraw.Draw(img)

    # Cadre décoratif patrimonial
    draw.rectangle([20, 20, 1180, 780], outline=(200, 185, 150), width=4)
    draw.rectangle([35, 35, 1165, 765], outline=(150, 135, 110), width=2)

    # Lignes décoratives
    draw.text((80, 300), title, fill=(240, 230, 210))
    draw.text((80, 360), subtitle, fill=(200, 190, 170))
    draw.text((80, 720), "Archives Patrimoniales - HierIci (Domaine Public)", fill=(160, 150, 130))

    img.save(output_path, "WEBP", quality=85)


async def seed():
    uploads_dir = Path(settings.LOCAL_STORAGE_PATH)
    uploads_dir.mkdir(parents=True, exist_ok=True)

    async with AsyncSessionLocal() as session:
        # 1. Récupération du territoire et de l'admin
        res_t = await session.execute(
            select(Territory).where(Territory.slug == settings.DEFAULT_TERRITORY_SLUG)
        )
        territory = res_t.scalar_one_or_none()
        if not territory:
            print("Erreur: Territoire pilote introuvable.")
            return

        res_u = await session.execute(
            select(User).where(User.email == settings.ADMIN_EMAIL)
        )
        admin = res_u.scalar_one_or_none()
        admin_id = admin.id if admin else None

        # 2. Photos d'archives géohistoriques de Toulon
        photos_data = [
            {
                "title": "La Rade de Toulon et l'Arsenal (1910)",
                "description": "Vue panoramique des cuirassés et des quais de l'arsenal maritime avant la Première Guerre mondiale.",
                "photographer": "Archives de la Marine",
                "year_taken": 1910,
                "period_label": "Belle Époque",
                "archive_source": "Archives Municipales de Toulon",
                "archive_ref": "AMT-1910-RAD-042",
                "license": "Domaine Public",
                "lat": 43.1215,
                "lng": 5.9260,
                "bearing": 160,
                "fov": 65,
                "prefix": "arsenal_1910",
                "color": (60, 50, 40),
            },
            {
                "title": "Fort Balaguier et la Petite Rade (1895)",
                "description": "Tour à canon fortifiée surveillant l'entrée de la petite rade et protégeant la rade de Toulon.",
                "photographer": "G. Bérenger",
                "year_taken": 1895,
                "period_label": "Fin XIXe",
                "archive_source": "Fonds Varois Historique",
                "archive_ref": "FVH-1895-BAL-108",
                "license": "Domaine Public",
                "lat": 43.0945,
                "lng": 5.9180,
                "bearing": 45,
                "fov": 60,
                "prefix": "balaguier_1895",
                "color": (50, 55, 60),
            },
            {
                "title": "Port Marchand et Quai Cronstadt (1935)",
                "description": "Pointements de barques marseillaises et voiliers le long du quai Cronstadt bordé de cafés d'époque.",
                "photographer": "Atelier Marius",
                "year_taken": 1935,
                "period_label": "Entre-deux-guerres",
                "archive_source": "Médiathèque du Port",
                "archive_ref": "MDP-1935-CRO-003",
                "license": "Domaine Public",
                "lat": 43.1200,
                "lng": 5.9320,
                "bearing": 210,
                "fov": 70,
                "prefix": "cronstadt_1935",
                "color": (65, 55, 45),
            },
            {
                "title": "La Tour Royale et la Passe des Vignettes (1944)",
                "description": "Forteresse historique dominant les passes lors des opérations navales de libération de Provence en août 1944.",
                "photographer": "Signal Corps US Army",
                "year_taken": 1944,
                "period_label": "Seconde Guerre mondiale",
                "archive_source": "NARA Archives",
                "archive_ref": "NARA-1944-PROV-712",
                "license": "Domaine Public",
                "lat": 43.1070,
                "lng": 5.9285,
                "bearing": 120,
                "fov": 55,
                "prefix": "tour_royale_1944",
                "color": (55, 50, 50),
            },
        ]

        created_photos = []
        for pdata in photos_data:
            prefix = pdata["prefix"]
            orig_rel = f"photos/{prefix}_original.webp"
            disp_rel = f"photos/{prefix}_display.webp"
            thumb_rel = f"photos/{prefix}_thumb.webp"

            generate_vintage_image(uploads_dir / orig_rel, pdata["title"], f"{pdata['period_label']} - {pdata['year_taken']}", pdata["color"])
            generate_vintage_image(uploads_dir / disp_rel, pdata["title"], f"{pdata['period_label']} - {pdata['year_taken']}", pdata["color"])
            generate_vintage_image(uploads_dir / thumb_rel, pdata["title"], str(pdata["year_taken"]), pdata["color"])

            pt = Point(pdata["lng"], pdata["lat"])
            photo = Photo(
                territory_id=territory.id,
                author_user_id=admin_id,
                title=pdata["title"],
                description=pdata["description"],
                photographer=pdata["photographer"],
                year_taken=pdata["year_taken"],
                period_label=pdata["period_label"],
                archive_source=pdata["archive_source"],
                archive_ref=pdata["archive_ref"],
                license=pdata["license"],
                latitude=pdata["lat"],
                longitude=pdata["lng"],
                location=from_shape(pt, srid=4326),
                bearing=pdata["bearing"],
                field_of_view=pdata["fov"],
                file_original_path=orig_rel,
                file_display_path=disp_rel,
                file_thumb_path=thumb_rel,
                status=PhotoStatus.PUBLISHED,
            )
            session.add(photo)
            created_photos.append(photo)

        await session.commit()
        for p in created_photos:
            await session.refresh(p)
        print(f"✅ {len(created_photos)} photos publiées créées avec succès.")

        # 3. Création d'une Storymap thématique complète
        cover_rel = "storymaps/rade_toulon_cover.webp"
        generate_vintage_image(
            uploads_dir / cover_rel,
            "La Rade de Toulon à travers les Siècles",
            "Parcours immersif géohistorique",
            (45, 55, 65),
        )

        storymap = Storymap(
            territory_id=territory.id,
            author_user_id=admin_id,
            slug="la-rade-de-toulon-a-travers-les-siecles",
            title="La Rade de Toulon à travers les Siècles",
            summary="Parcours géohistorique immersif explorant l'évolution stratégique, militaire et maritime de la rade de Toulon, du XIXe siècle à la Libération de Provence en 1944.",
            cover_image_path=cover_rel,
            status=StorymapStatus.PUBLISHED,
        )
        session.add(storymap)
        await session.commit()
        await session.refresh(storymap)

        # 4. Étapes (Chapitres) de la storymap
        steps_data = [
            {
                "photo": created_photos[0],
                "title": "L'Arsenal maritime et les cuirassés",
                "markdown": "### Le cœur stratégique de la flotte\n\nÀ l'aube du XXe siècle, l'arsenal de Toulon est l'un des plus puissants complexes militaro-industriels de Méditerranée. Les grands bassins Vauban et Castigneau accueillent les fleurons de l'escadre française.\n\n*Observez la ligne de flottaison et l'alignement des grues à vapeur le long des quais.*",
                "lat": 43.1215,
                "lng": 5.9260,
                "zoom": 15.5,
                "bearing": 160,
                "pitch": 45,
            },
            {
                "photo": created_photos[1],
                "title": "Fort Balaguier et la surveillance des passes",
                "markdown": "### La sentinelle de la rade\n\nÉdifié dès le XVIIe siècle pour interdire l'accès de la petite rade aux escadres ennemies, le **Fort Balaguier** offre un point d'observation remarquable sur la rade des Vignettes.\n\nSes bouches à feu croisaient leurs tirs avec celles de la Tour Royale.",
                "lat": 43.0945,
                "lng": 5.9180,
                "zoom": 16.0,
                "bearing": 45,
                "pitch": 55,
            },
            {
                "photo": created_photos[2],
                "title": "La vie quotidienne sur le Quai Cronstadt",
                "markdown": "### Entre marins et civils\n\nDans les années 1930, le quai Cronstadt concentre l'animation populaire de Toulon. Barques de pêcheurs, débits de boisson et promenades familiales s'y côtoient sous le soleil varois.",
                "lat": 43.1200,
                "lng": 5.9320,
                "zoom": 16.2,
                "bearing": 210,
                "pitch": 40,
            },
            {
                "photo": created_photos[3],
                "title": "La Tour Royale et la Libération de 1944",
                "markdown": "### L'épreuve du feu et la liberté retrouvée\n\nEn août 1944, l'opération Anvil-Dragoon libère la Provence. Les forces de l'Armée B du général de Lattre de Tassigny prennent d'assaut les réduits fortifiés de la rade.\n\nLa Tour Royale, symbole plusieurs fois centenaire, retrouve son pavillon national.",
                "lat": 43.1070,
                "lng": 5.9285,
                "zoom": 15.8,
                "bearing": 120,
                "pitch": 60,
            },
        ]

        for order, sdata in enumerate(steps_data):
            step = StorymapStep(
                storymap_id=storymap.id,
                photo_id=sdata["photo"].id,
                step_order=order,
                title=sdata["title"],
                content_markdown=sdata["markdown"],
                camera_lat=sdata["lat"],
                camera_lng=sdata["lng"],
                camera_zoom=sdata["zoom"],
                camera_bearing=sdata["bearing"],
                camera_pitch=sdata["pitch"],
            )
            session.add(step)

        # Deuxième storymap pour enrichir le catalogue !
        cover2_rel = "storymaps/fortifications_cover.webp"
        generate_vintage_image(
            uploads_dir / cover2_rel,
            "Les Sentinelles de Granit de la Côte Varoise",
            "Parcours défensif et architectures militaires",
            (55, 60, 50),
        )

        storymap2 = Storymap(
            territory_id=territory.id,
            author_user_id=admin_id,
            slug="les-sentinelles-de-granit",
            title="Les Sentinelles de Granit de la Côte Varoise",
            summary="Une découverte panoramique des ouvrages de défense côtière, des bastions royaux du XVIIe siècle aux batteries d'artillerie côtière.",
            cover_image_path=cover2_rel,
            status=StorymapStatus.PUBLISHED,
        )
        session.add(storymap2)
        await session.commit()
        await session.refresh(storymap2)

        step_s2 = StorymapStep(
            storymap_id=storymap2.id,
            photo_id=created_photos[1].id,
            step_order=0,
            title="Le Verrou de Balaguier",
            content_markdown="### Une architecture militaire pérenne\n\nConstruit pour barrer la rade, le fort témoigne des techniques d'artillerie côtière d'Ancien Régime.",
            camera_lat=43.0945,
            camera_lng=5.9180,
            camera_zoom=16.0,
            camera_bearing=45,
            camera_pitch=50,
        )
        session.add(step_s2)

        await session.commit()
        print(f"✅ 2 storymaps publiées avec leurs chapitres créées.")


if __name__ == "__main__":
    asyncio.run(seed())

