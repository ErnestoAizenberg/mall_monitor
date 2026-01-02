import requests
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
import os
from jinja2 import Template

@dataclass
class Point:
    id: str
    name: str
    parsed_categories: List[str] = field(default_factory=list)
    assigned_categories: List[str] = field(default_factory=list)
    parsing_date: str = ""
    status: str = "opened"

@dataclass
class ChangeReport:
    date: str
    total_before: int
    total_after: int
    new_shops: List[Point]
    disappeared_shops: List[Point]
    changed_shops: List[Dict[str, Any]]
    stats: Dict[str, Any]

def load_old_shops(filename: Optional[str] = None) -> List[Point]:
    if filename is None:
        filename = DATA_FILE

    if not os.path.exists(filename):
        print(f"Файл {filename} не найден. Будет создан новый.")
        return []

    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)

        old_shops = []
        for item in data:
            shop = Point(
                id=item.get('id', ''),
                name=item.get('name', ''),
                parsed_categories=item.get('parsed_categories', []),
                assigned_categories=item.get('assigned_categories', []),
                parsing_date=item.get('parsing_date', ''),
                status=item.get('status', 'unknown')
            )
            old_shops.append(shop)

        return old_shops
    except Exception as e:
        print(f"Ошибка при загрузке файла: {e}")
        return []

def save_new_shops(shops: List[Point], filename: str):
    os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else '.', exist_ok=True)

    data_to_save = []
    for shop in shops:
        data_to_save.append(asdict(shop))

    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=2)
        print(f"✓ Основные данные сохранены в {filename}")
    except Exception as e:
        print(f"✗ Ошибка при сохранении: {e}")

def normalize_name(name: str) -> str:
    return name.strip().lower()

def analyze_changes(old_shops: List[Point], new_shops: List[Point]) -> ChangeReport:
    old_dict = {normalize_name(shop.name): shop for shop in old_shops}
    new_dict = {normalize_name(shop.name): shop for shop in new_shops}

    old_names = set(old_dict.keys())
    new_names = set(new_dict.keys())

    appeared_names = new_names - old_names
    disappeared_names = old_names - new_names
    remaining_names = old_names & new_names

    new_shops_list = [new_dict[name] for name in appeared_names]
    disappeared_shops_list = [old_dict[name] for name in disappeared_names]

    changed_shops_list = []
    for name in remaining_names:
        old_shop = old_dict[name]
        new_shop = new_dict[name]

        changes = {}

        if old_shop.id != new_shop.id:
            changes['id'] = {'old': old_shop.id, 'new': new_shop.id}

        if old_shop.status != new_shop.status:
            changes['status'] = {'old': old_shop.status, 'new': new_shop.status}

        old_cats = set(old_shop.parsed_categories)
        new_cats = set(new_shop.parsed_categories)

        if old_cats != new_cats:
            added = list(new_cats - old_cats)
            removed = list(old_cats - new_cats)

            if added or removed:
                changes['categories'] = {
                    'added': added,
                    'removed': removed,
                    'total_old': len(old_cats),
                    'total_new': len(new_cats)
                }

        if changes:
            changed_shops_list.append({
                'name': old_shop.name,
                'old_shop': asdict(old_shop),
                'new_shop': asdict(new_shop),
                'changes': changes
            })

    stats = {
        'total_before': len(old_shops),
        'total_after': len(new_shops),
        'new_count': len(new_shops_list),
        'disappeared_count': len(disappeared_shops_list),
        'changed_count': len(changed_shops_list),
        'unchanged_count': len(remaining_names) - len(changed_shops_list),
        'change_percentage': round((len(new_shops) - len(old_shops)) / max(len(old_shops), 1) * 100, 2)
    }

    report = ChangeReport(
        date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        total_before=len(old_shops),
        total_after=len(new_shops),
        new_shops=new_shops_list,
        disappeared_shops=disappeared_shops_list,
        changed_shops=changed_shops_list,
        stats=stats
    )

    return report

def save_report_to_json(report: ChangeReport):
    reports_dir = "reports"
    os.makedirs(reports_dir, exist_ok=True)

    latest_file = os.path.join(reports_dir, "latest_report.json")
    date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    history_file = os.path.join(reports_dir, f"report_{date_str}.json")

    report_dict = asdict(report)

    try:
        with open(latest_file, 'w', encoding='utf-8') as f:
            json.dump(report_dict, f, ensure_ascii=False, indent=2)
        print(f"✓ Последний отчёт сохранён в {latest_file}")

        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(report_dict, f, ensure_ascii=False, indent=2)
        print(f"✓ Исторический отчёт сохранён в {history_file}")

    except Exception as e:
        print(f"✗ Ошибка при сохранении отчёта: {e}")

def generate_html_report(report: ChangeReport):
    html_template = """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Отчёт по магазинам Авиапарк</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css">
    <style>
        .stat-card {
            transition: transform 0.2s;
            border-left: 4px solid;
        }
        .stat-card:hover {
            transform: translateY(-3px);
        }
        .shop-card {
            border-left: 4px solid;
            transition: all 0.2s;
        }
        .shop-card:hover {
            box-shadow: 0 .5rem 1rem rgba(0,0,0,.15);
        }
        .new-shop { border-left-color: #28a745; }
        .disappeared-shop { border-left-color: #dc3545; }
        .changed-shop { border-left-color: #ffc107; }
        .category-badge {
            font-size: 0.75rem;
        }
        .change-badge {
            font-size: 0.8rem;
        }
    </style>
</head>
<body class="bg-light">
    <div class="container py-4">
        <header class="text-center mb-5">
            <h1 class="display-4 text-primary mb-3">
                <i class="bi bi-shop"></i> Отчёт по магазинам Авиапарк
            </h1>
            <p class="lead text-muted">Мониторинг изменений в торговом центре</p>
            <div class="badge bg-secondary fs-6">
                <i class="bi bi-calendar"></i> Дата отчёта: {{ report_date }}
            </div>
        </header>

        <section class="mb-5">
            <h2 class="h4 mb-4">📊 Общая статистика</h2>
            <div class="row g-4">
                <div class="col-md-6 col-lg-4">
                    <div class="stat-card card h-100 border-left-primary">
                        <div class="card-body text-center">
                            <h6 class="card-subtitle mb-2 text-muted">Было магазинов</h6>
                            <h3 class="card-title display-6">{{ total_before }}</h3>
                        </div>
                    </div>
                </div>
                <div class="col-md-6 col-lg-4">
                    <div class="stat-card card h-100 border-left-primary">
                        <div class="card-body text-center">
                            <h6 class="card-subtitle mb-2 text-muted">Стало магазинов</h6>
                            <h3 class="card-title display-6">{{ total_after }}</h3>
                        </div>
                    </div>
                </div>
                <div class="col-md-6 col-lg-4">
                    <div class="stat-card card h-100 border-left-{{ 'success' if change_percentage > 0 else 'danger' if change_percentage < 0 else 'secondary' }}">
                        <div class="card-body text-center">
                            <h6 class="card-subtitle mb-2 text-muted">Изменение</h6>
                            <h3 class="card-title display-6">{{ change_percentage }}%</h3>
                        </div>
                    </div>
                </div>
            </div>
        </section>

        <section class="mb-5">
            <h2 class="h4 mb-4">
                <span class="badge bg-success"><i class="bi bi-plus-lg"></i> {{ new_count }}</span>
                Новые магазины
            </h2>
            {% if new_shops %}
                <div class="row g-3">
                    {% for shop in new_shops %}
                    <div class="col-12">
                        <div class="shop-card new-shop card">
                            <div class="card-body">
                                <h5 class="card-title">
                                    <i class="bi bi-plus-circle text-success"></i> {{ shop.name }}
                                </h5>
                                <p class="card-text text-muted mb-2">
                                    <small>ID: {{ shop.id }} | Статус: {{ shop.status }}</small>
                                </p>
                                {% if shop.parsed_categories %}
                                <div class="mb-3">
                                    {% for category in shop.parsed_categories %}
                                    <span class="category-badge badge bg-light text-dark me-1">{{ category }}</span>
                                    {% endfor %}
                                </div>
                                {% endif %}
                                <p class="card-text">
                                    <small class="text-muted">
                                        <i class="bi bi-clock"></i> Добавлен: {{ shop.parsing_date }}
                                    </small>
                                </p>
                            </div>
                        </div>
                    </div>
                    {% endfor %}
                </div>
            {% else %}
                <div class="alert alert-success">
                    <i class="bi bi-check-circle"></i> Новых магазинов нет — всё стабильно!
                </div>
            {% endif %}
        </section>

        <section class="mb-5">
            <h2 class="h4 mb-4">
                <span class="badge bg-danger"><i class="bi bi-dash-lg"></i> {{ disappeared_count }}</span>
                Исчезнувшие магазины
            </h2>
            {% if disappeared_shops %}
                <div class="row g-3">
                    {% for shop in disappeared_shops %}
                    <div class="col-12">
                        <div class="shop-card disappeared-shop card">
                            <div class="card-body">
                                <h5 class="card-title">
                                    <i class="bi bi-dash-circle text-danger"></i> {{ shop.name }}
                                </h5>
                                <p class="card-text text-muted mb-2">
                                    <small>ID: {{ shop.id }} | Статус: {{ shop.status }}</small>
                                </p>
                                {% if shop.parsed_categories %}
                                <div class="mb-3">
                                    {% for category in shop.parsed_categories %}
                                    <span class="category-badge badge bg-light text-dark me-1">{{ category }}</span>
                                    {% endfor %}
                                </div>
                                {% endif %}
                                <p class="card-text">
                                    <small class="text-muted">
                                        <i class="bi bi-clock"></i> Был в системе: {{ shop.parsing_date }}
                                    </small>
                                </p>
                            </div>
                        </div>
                    </div>
                    {% endfor %}
                </div>
            {% else %}
                <div class="alert alert-success">
                    <i class="bi bi-check-circle"></i> Ни один магазин не исчез!
                </div>
            {% endif %}
        </section>

        <section class="mb-5">
            <h2 class="h4 mb-4">
                <span class="badge bg-warning text-dark"><i class="bi bi-pencil"></i> {{ changed_count }}</span>
                Изменённые магазины
            </h2>
            {% if changed_shops %}
                <div class="row g-3">
                    {% for shop in changed_shops %}
                    <div class="col-12">
                        <div class="shop-card changed-shop card">
                            <div class="card-body">
                                <h5 class="card-title">
                                    <i class="bi bi-pencil-square text-warning"></i> {{ shop.name }}
                                </h5>
                                <p class="card-text text-muted mb-2">
                                    <small>ID: {{ shop.old_shop.id }}</small>
                                </p>

                                <div class="changes mt-3">
                                    {% if shop.changes.id %}
                                    <div class="alert alert-warning change-badge">
                                        <i class="bi bi-arrow-left-right"></i> ID изменился:
                                        <strong>{{ shop.changes.id.old }}</strong> →
                                        <strong>{{ shop.changes.id.new }}</strong>
                                    </div>
                                    {% endif %}

                                    {% if shop.changes.status %}
                                    <div class="alert alert-warning change-badge">
                                        <i class="bi bi-arrow-left-right"></i> Статус изменился:
                                        <strong>{{ shop.changes.status.old }}</strong> →
                                        <strong>{{ shop.changes.status.new }}</strong>
                                    </div>
                                    {% endif %}

                                    {% if shop.changes.categories %}
                                    <div class="alert alert-info change-badge">
                                        <i class="bi bi-tags"></i> Категории:
                                        <strong>{{ shop.changes.categories.total_old }}</strong> →
                                        <strong>{{ shop.changes.categories.total_new }}</strong>

                                        {% if shop.changes.categories.added %}
                                        <div class="mt-2">
                                            <span class="badge bg-success">
                                                <i class="bi bi-plus"></i> Добавлены:
                                            </span>
                                            {% for category in shop.changes.categories.added %}
                                            <span class="badge bg-light text-dark ms-1">{{ category }}</span>
                                            {% endfor %}
                                        </div>
                                        {% endif %}

                                        {% if shop.changes.categories.removed %}
                                        <div class="mt-2">
                                            <span class="badge bg-danger">
                                                <i class="bi bi-dash"></i> Удалены:
                                            </span>
                                            {% for category in shop.changes.categories.removed %}
                                            <span class="badge bg-light text-dark ms-1">{{ category }}</span>
                                            {% endfor %}
                                        </div>
                                        {% endif %}
                                    </div>
                                    {% endif %}
                                </div>
                            </div>
                        </div>
                    </div>
                    {% endfor %}
                </div>
            {% else %}
                <div class="alert alert-success">
                    <i class="bi bi-check-circle"></i> Изменений в магазинах не обнаружено
                </div>
            {% endif %}
        </section>

        <footer class="mt-5 pt-4 border-top text-center text-muted">
            <p class="mb-1">
                <i class="bi bi-graph-up"></i> Отчёт сгенерирован автоматически | Авиапарк мониторинг
            </p>
            <p class="small">
                Всего обработано магазинов: {{ total_after }} | Обновлено: {{ report_date }}
            </p>
        </footer>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>"""

    change_percentage = report.stats['change_percentage']
    change_color = "success" if change_percentage > 0 else "danger" if change_percentage < 0 else "secondary"

    template_data = {
        'report_date': report.date,
        'total_before': report.total_before,
        'total_after': report.total_after,
        'new_count': report.stats['new_count'],
        'disappeared_count': report.stats['disappeared_count'],
        'changed_count': report.stats['changed_count'],
        'change_percentage': change_percentage,
        'change_color': change_color,
        'new_shops': [asdict(shop) for shop in report.new_shops],
        'disappeared_shops': [asdict(shop) for shop in report.disappeared_shops],
        'changed_shops': report.changed_shops
    }

    template = Template(html_template)
    html_content = template.render(**template_data)

    reports_dir = "reports"
    os.makedirs(reports_dir, exist_ok=True)

    html_file = os.path.join(reports_dir, "report.html")

    try:
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"✓ HTML отчёт сохранён в {html_file}")

        date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        history_html_file = os.path.join(reports_dir, f"report_{date_str}.html")
        with open(history_html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"✓ Исторический HTML отчёт сохранён в {history_html_file}")

    except Exception as e:
        print(f"✗ Ошибка при сохранении HTML: {e}")

def parse_riviera(filename: str):
    old_shops = load_old_shops(filename)
    print(f"📊 Магазинов было: {len(old_shops)}")

    new_shop_list = []

    print("🔄 Начинаем парсинг...")

    url = 'https://api.riviera.su/api/v1/tenants?category&limit=1500'
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"❌ Ошибка при запросе: {e}")
        return

    for s in data['payload']['data']:
        shop = Point(
            id=s.get('id'),
            name=s.get('title'),
            parsed_categories=[],
            parsing_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            status=s.get("status", "unknown")
        )
        new_shop_list.append(shop)

    print(f"📊 Магазинов стало: {len(new_shop_list)}")

    report = analyze_changes(old_shops, new_shop_list)

    save_new_shops(new_shop_list, filename)

    save_report_to_json(report)

    generate_html_report(report)

    return report

def parse_aviapark(filename: str):

    old_shops = load_old_shops(filename)
    print(f"📊 Магазинов было: {len(old_shops)}")

    new_shop_list = []

    print("🔄 Начинаем парсинг...")
    url = "https://api.aviapark.com/v1/departments"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"❌ Ошибка при запросе: {e}")
        return

    for s in data['departments']:
        shop = Point(
            id=s.get("id", ""),
            name=s.get("title", ""),
            parsed_categories=s.get("categories", []),
            parsing_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            status=s.get("status", "unknown")
        )
        new_shop_list.append(shop)

    print(f"📊 Магазинов стало: {len(new_shop_list)}")

    report = analyze_changes(old_shops, new_shop_list)

    save_new_shops(new_shop_list, filename)

    save_report_to_json(report)

    generate_html_report(report)

    return report

def main():
    print("="*60)
    print("🛍️  ПАРСЕР АВИАПАРК - МОНИТОРИНГ ИЗМЕНЕНИЙ")
    print("="*60)

    report = parse_aviapark(filename="data/aviapark.json")

    if report:
        print("\n" + "="*60)
        print("📈 КРАТКАЯ СТАТИСТИКА:")
        print(f"   • Новых магазинов: {report.stats['new_count']}")
        print(f"   • Исчезнувших магазинов: {report.stats['disappeared_count']}")
        print(f"   • Изменённых магазинов: {report.stats['changed_count']}")
        print(f"   • Изменение: {report.stats['change_percentage']}%")
        print("="*60)

        print("\n📁 Отчёты сохранены в папке 'reports/':")
        print("   • report.html - HTML отчёт для просмотра")
        print("   • latest_report.json - последний отчёт в JSON")
        print("   • report_*.json - исторические отчёты")

    print("\n" + "="*60)
    print("✅ ВЫПОЛНЕНО!")
    print("="*60)

if __name__ == "__main__":
    main()
