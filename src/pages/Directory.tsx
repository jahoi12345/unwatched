import { useMemo, useState } from 'react';
import { categories, tools, type Category } from '../data/tools';

type Filter = 'all' | Category;

export default function Directory() {
	const [query, setQuery] = useState('');
	const [activeFilter, setActiveFilter] = useState<Filter>('all');

	const normalizedQuery = query.trim().toLowerCase();

	const visibleByCategory = useMemo(() => {
		return categories.map((cat) => {
			const categoryMatches = activeFilter === 'all' || activeFilter === cat.id;
			const catTools = categoryMatches
				? tools.filter((tool) => {
						if (tool.category !== cat.id) return false;
						if (normalizedQuery === '') return true;
						return (
							tool.name.toLowerCase().includes(normalizedQuery) ||
							tool.description.toLowerCase().includes(normalizedQuery)
						);
					})
				: [];
			return { ...cat, tools: catTools };
		});
	}, [activeFilter, normalizedQuery]);

	const anyVisible = visibleByCategory.some((cat) => cat.tools.length > 0);

	return (
		<>
			<div className="controls">
				<input
					type="search"
					aria-label="Search tools"
					placeholder="Search tools…"
					value={query}
					onChange={(e) => setQuery(e.target.value)}
				/>
				<button
					className="chip"
					aria-pressed={activeFilter === 'all'}
					onClick={() => setActiveFilter('all')}
				>
					All
				</button>
				{categories.map((cat) => (
					<button
						key={cat.id}
						className="chip"
						aria-pressed={activeFilter === cat.id}
						onClick={() => setActiveFilter(cat.id)}
					>
						{cat.label}
					</button>
				))}
			</div>

			<main>
				{visibleByCategory.map(
					(cat) =>
						cat.tools.length > 0 && (
							<section className="category-block" key={cat.id}>
								<h2>{cat.label}</h2>
								<p className="cat-desc">{cat.description}</p>
								<div className="grid">
									{cat.tools.map((tool) => (
										<a
											key={tool.name}
											className="card"
											href={tool.url}
											target="_blank"
											rel="noopener noreferrer"
										>
											<div className="name">
												<span>{tool.name}</span>
												<span className="arrow" aria-hidden="true">
													↗
												</span>
											</div>
											<div className="desc">{tool.description}</div>
										</a>
									))}
								</div>
							</section>
						),
				)}
				{!anyVisible && (
					<p className="empty-state" style={{ display: 'block' }}>
						No tools match your search.
					</p>
				)}
			</main>
		</>
	);
}
