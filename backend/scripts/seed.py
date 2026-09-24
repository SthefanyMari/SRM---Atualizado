import asyncio

from sqlalchemy import select

from app.core.config import settings
from app.core.database import SessionLocal, close_database, create_tables
from app.core.security import hash_password
from app.models import Content, ContentDomainRecord, User, UserPreference


DOMAINS = [
    ("filme", "Filmes", "Cinema, documentários e produções audiovisuais."),
    ("musica", "Músicas", "Canções, álbuns, artistas e estilos musicais."),
    ("livro", "Livros", "Romances, não ficção, fantasia e outros gêneros."),
    ("curso", "Cursos", "Formações e conteúdos para aprender novas habilidades."),
    ("produto", "Produtos", "Tecnologia, leitura, áudio e itens para o dia a dia."),
]


CONTENTS = [
    {
        "title": "Interestelar",
        "description": "Uma viagem espacial sobre tempo, família e sobrevivência da humanidade.",
        "domain": "filme",
        "category": "Ficção científica",
        "external_id": "movie-interstellar",
        "metadata": {"year": 2014, "duration": "2h49"},
    },
    {
        "title": "A Chegada",
        "description": "Uma linguista tenta compreender visitantes extraterrestres e sua forma de perceber o tempo.",
        "domain": "filme",
        "category": "Ficção científica",
        "external_id": "movie-arrival",
        "metadata": {"year": 2016, "duration": "1h56"},
    },
    {
        "title": "O Senhor dos Anéis",
        "description": "Uma jornada de amizade, coragem e fantasia pela Terra-média.",
        "domain": "livro",
        "category": "Fantasia",
        "external_id": "book-lord-rings",
        "metadata": {"author": "J. R. R. Tolkien"},
    },
    {
        "title": "1984",
        "description": "Um romance sobre vigilância, poder e liberdade em uma sociedade autoritária.",
        "domain": "livro",
        "category": "Distopia",
        "external_id": "book-1984",
        "metadata": {"author": "George Orwell"},
    },
    {
        "title": "Python para Iniciantes",
        "description": "Curso prático de programação em Python, lógica, funções e projetos simples.",
        "domain": "curso",
        "category": "Programação",
        "external_id": "course-python",
        "metadata": {"level": "Iniciante", "hours": 20},
    },
    {
        "title": "Segurança da Informação",
        "description": "Curso introdutório sobre autenticação, criptografia, riscos e proteção de dados.",
        "domain": "curso",
        "category": "Tecnologia",
        "external_id": "course-security",
        "metadata": {"level": "Intermediário", "hours": 16},
    },
    {
        "title": "Clair de Lune",
        "description": "Composição de Claude Debussy com atmosfera calma e contemplativa.",
        "domain": "musica",
        "category": "Clássica",
        "external_id": "music-clair-lune",
        "metadata": {"artist": "Claude Debussy"},
    },
    {
        "title": "Here Comes the Sun",
        "description": "Canção leve e otimista sobre a chegada de dias melhores.",
        "domain": "musica",
        "category": "Rock clássico",
        "external_id": "music-here-sun",
        "metadata": {"artist": "The Beatles"},
    },
    {
        "title": "Kindle Paperwhite",
        "description": "Leitor digital com iluminação ajustável e tela antirreflexo.",
        "domain": "produto",
        "category": "Leitura",
        "external_id": "product-kindle",
        "metadata": {"brand": "Amazon"},
    },
    {
        "title": "Fone com cancelamento de ruído",
        "description": "Fone sem fio pensado para música, estudo e concentração.",
        "domain": "produto",
        "category": "Áudio",
        "external_id": "product-headphone",
        "metadata": {"connection": "Bluetooth"},
    },
    {
        "title": "O Show de Truman",
        "description": "Um homem descobre que sua vida inteira faz parte de um programa de televisão.",
        "domain": "filme",
        "category": "Comédia dramática",
        "external_id": "movie-truman-show",
        "metadata": {"year": 1998},
    },
    {
        "title": "Divertida Mente",
        "description": "As emoções de uma garota precisam trabalhar juntas durante uma grande mudança.",
        "domain": "filme",
        "category": "Animação",
        "external_id": "movie-inside-out",
        "metadata": {"year": 2015},
    },
    {
        "title": "Parasita",
        "description": "Duas famílias de realidades opostas se aproximam de forma inesperada.",
        "domain": "filme",
        "category": "Suspense",
        "external_id": "movie-parasite",
        "metadata": {"year": 2019},
    },
    {
        "title": "Homem-Aranha no Aranhaverso",
        "description": "Miles Morales encontra diferentes versões do Homem-Aranha em uma aventura animada.",
        "domain": "filme",
        "category": "Animação e aventura",
        "external_id": "movie-spider-verse",
        "metadata": {"year": 2018},
    },
    {
        "title": "Dom Casmurro",
        "description": "Bentinho relembra sua juventude e sua relação com Capitu.",
        "domain": "livro",
        "category": "Literatura brasileira",
        "external_id": "book-dom-casmurro",
        "metadata": {"author": "Machado de Assis"},
    },
    {
        "title": "O Pequeno Príncipe",
        "description": "Uma história sobre amizade, responsabilidade e o que realmente importa.",
        "domain": "livro",
        "category": "Fábula",
        "external_id": "book-little-prince",
        "metadata": {"author": "Antoine de Saint-Exupéry"},
    },
    {
        "title": "Sapiens",
        "description": "Uma visão ampla da história e do desenvolvimento da humanidade.",
        "domain": "livro",
        "category": "História",
        "external_id": "book-sapiens",
        "metadata": {"author": "Yuval Noah Harari"},
    },
    {
        "title": "Hábitos Atômicos",
        "description": "Estratégias práticas para criar bons hábitos e abandonar comportamentos ruins.",
        "domain": "livro",
        "category": "Desenvolvimento pessoal",
        "external_id": "book-atomic-habits",
        "metadata": {"author": "James Clear"},
    },
    {
        "title": "Bohemian Rhapsody",
        "description": "Canção do Queen que combina rock, balada e elementos operísticos.",
        "domain": "musica",
        "category": "Rock",
        "external_id": "music-bohemian-rhapsody",
        "metadata": {"artist": "Queen"},
    },
    {
        "title": "Garota de Ipanema",
        "description": "Um clássico brasileiro conhecido mundialmente pela leveza da bossa nova.",
        "domain": "musica",
        "category": "Bossa nova",
        "external_id": "music-garota-ipanema",
        "metadata": {"artist": "Tom Jobim e Vinicius de Moraes"},
    },
    {
        "title": "Blinding Lights",
        "description": "Faixa pop com sintetizadores e forte influência dos anos 1980.",
        "domain": "musica",
        "category": "Pop",
        "external_id": "music-blinding-lights",
        "metadata": {"artist": "The Weeknd"},
    },
    {
        "title": "Trem-Bala",
        "description": "Canção brasileira sobre afetos, tempo e as pessoas importantes da vida.",
        "domain": "musica",
        "category": "MPB",
        "external_id": "music-trem-bala",
        "metadata": {"artist": "Ana Vilela"},
    },
    {
        "title": "CS50: Introdução à Ciência da Computação",
        "description": "Curso introdutório de Harvard sobre algoritmos, programação e estruturas de dados.",
        "domain": "curso",
        "category": "Ciência da computação",
        "external_id": "course-cs50",
        "metadata": {"institution": "Harvard"},
    },
    {
        "title": "Google Data Analytics",
        "description": "Formação sobre análise, limpeza, visualização e interpretação de dados.",
        "domain": "curso",
        "category": "Dados",
        "external_id": "course-google-data",
        "metadata": {"institution": "Google"},
    },
    {
        "title": "Introdução ao Design UX",
        "description": "Curso sobre pesquisa com usuários, protótipos e melhoria de experiências digitais.",
        "domain": "curso",
        "category": "Design",
        "external_id": "course-ux-intro",
        "metadata": {"level": "Iniciante"},
    },
    {
        "title": "Inglês para Comunicação",
        "description": "Prática de vocabulário e conversação para situações comuns do cotidiano.",
        "domain": "curso",
        "category": "Idiomas",
        "external_id": "course-english-communication",
        "metadata": {"level": "Básico"},
    },
    {
        "title": "Kobo Libra Colour",
        "description": "Leitor digital com tela colorida, botões laterais e suporte a anotações.",
        "domain": "produto",
        "category": "Leitura",
        "external_id": "product-kobo-libra-colour",
        "metadata": {"brand": "Kobo"},
    },
    {
        "title": "Logitech MX Master 3S",
        "description": "Mouse sem fio voltado para produtividade, conforto e precisão.",
        "domain": "produto",
        "category": "Informática",
        "external_id": "product-mx-master-3s",
        "metadata": {"brand": "Logitech"},
    },
    {
        "title": "Sony WH-1000XM5",
        "description": "Fone Bluetooth com cancelamento de ruído e controles por toque.",
        "domain": "produto",
        "category": "Áudio",
        "external_id": "product-sony-wh1000xm5",
        "metadata": {"brand": "Sony"},
    },
    {
        "title": "Raspberry Pi 5",
        "description": "Computador compacto para estudos, automação e projetos de programação.",
        "domain": "produto",
        "category": "Tecnologia",
        "external_id": "product-raspberry-pi-5",
        "metadata": {"brand": "Raspberry Pi"},
    },
]


async def ensure_user(name: str, email: str, password: str, role: str) -> User:
    async with SessionLocal() as db:
        user = await db.scalar(select(User).where(User.email == email.lower()))
        if user is None:
            user = User(
                name=name,
                email=email.lower(),
                password_hash=hash_password(password),
                role=role,
                is_active=True,
            )
            db.add(user)
            await db.flush()
            db.add(
                UserPreference(
                    user_id=user.id,
                    profile={
                        "preferred_domains": ["filme", "livro", "curso"],
                        "preferred_categories": ["Tecnologia", "Ficção científica"],
                    },
                )
            )
            await db.commit()
        return user


async def main() -> None:
    await create_tables()
    async with SessionLocal() as db:
        for code, name, description in DOMAINS:
            domain = await db.scalar(
                select(ContentDomainRecord).where(ContentDomainRecord.code == code)
            )
            if domain is None:
                db.add(
                    ContentDomainRecord(
                        code=code,
                        name=name,
                        description=description,
                        is_active=True,
                    )
                )
            else:
                domain.name = name
                domain.description = description
        await db.commit()

    await ensure_user(
        settings.admin_name,
        str(settings.admin_email),
        settings.admin_password,
        "admin",
    )
    await ensure_user(
        settings.demo_user_name,
        str(settings.demo_user_email),
        settings.demo_user_password,
        "user",
    )

    async with SessionLocal() as db:
        for item in CONTENTS:
            existing = await db.scalar(
                select(Content.id).where(
                    Content.source_name == "seed",
                    Content.external_id == item["external_id"],
                )
            )
            if existing:
                continue
            values = dict(item)
            values["extra_data"] = values.pop("metadata")
            db.add(Content(source_name="seed", is_published=True, **values))
        await db.commit()

    await close_database()
    print("Dados de exemplo inseridos sem duplicação.")


if __name__ == "__main__":
    asyncio.run(main())
