import { AdjustmentReason } from '$lib/api/ingredients';

export const UNIT_OPTIONS = {
	weight: [
		{ id: 'g', name: 'Gramos (g)' },
		{ id: 'kg', name: 'Kilogramos (kg)' },
		{ id: 'oz', name: 'Onzas (oz)' },
		{ id: 'lb', name: 'Libras (lb)' }
	],
	volume: [
		{ id: 'ml', name: 'Mililitros (ml)' },
		{ id: 'L', name: 'Litros (L)' },
		{ id: 'fl_oz', name: 'Onzas Líquidas (fl oz)' }
	],
	unit: [
		{ id: 'pz', name: 'Piezas (pz)' },
		{ id: 'ud', name: 'Unidades' },
		{ id: 'porcion', name: 'Porción' }
	]
};

export const MEASURE_TYPES = [
	{ id: 'weight', name: 'Sólido / Peso', icon: '⚖️' },
	{ id: 'volume', name: 'Líquido / Volumen', icon: '💧' },
	{ id: 'unit', name: 'Pieza / Unidad', icon: '📦' }
];

export const REASON_LABELS = {
	[AdjustmentReason.WASTE]: 'Desperdicio',
	[AdjustmentReason.EXPIRED]: 'Caducado',
	[AdjustmentReason.ERROR]: 'Error de Prep',
	[AdjustmentReason.THEFT]: 'Robo',
	[AdjustmentReason.PERSONAL_CONSUMPTION]: 'Consumo Personal',
	[AdjustmentReason.PURCHASE]: 'Compra',
	[AdjustmentReason.RESTOCK]: 'Reposición',
	[AdjustmentReason.PHYSICAL_COUNT]: 'Conteo Físico',
	[AdjustmentReason.CORRECTION]: 'Corrección'
};
