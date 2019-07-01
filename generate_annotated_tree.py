"""
	Annotates a phylogenic tree using a pre-generated newick file and the comparison table generated by the isolate_parsers package.
"""
import argparse
import re
from pathlib import Path
from typing import Dict, List
from ete3 import TextFace, Tree
import pandas


def create_parser() -> argparse.ArgumentParser:
	parser = argparse.ArgumentParser()
	parser.add_argument(
		"filename",
		help = "The comparison table generated by the isolate_parsers package. Should be an excel file.",
		type = Path
	)

	parser.add_argument("tree", help = "A pre-generated tree in newick format.", type = Path)
	parser.add_argument("output", help = "Filename for the output svg file.")

	return parser


def find_ortholog(locus_tag: str, locus_tag_map: Dict[str, str]):
	pattern = "[A-Z]{8}_[\d]+"  # Prokka locus tag format
	locus_tags = re.findall(pattern, locus_tag)
	remapped_tags = [locus_tag_map.get(i, i) for i in locus_tags]
	new_tag = " - ".join(remapped_tags)
	if new_tag:
		return new_tag
	else:
		return locus_tag.replace(' -', '')


def get_common_mutations(comparison: pandas.DataFrame, samples: List[str]) -> List[str]:
	""" Gets a list of mutations that only appear in these samples.
		Parameters
		----------
		comparison: pandas.DataFrame
		samples: List[str]
			A list of the sample ids or names to get common mutations for.
	"""
	sample_columns = [i for i in comparison_table.columns if '-' in i]
	other_columns = [i for i in comparison_table.columns if i not in sample_columns]
	reduced = comparison[samples + other_columns]

	# Find all sites that contain the mutation.
	selection = reduced[samples[0]] != reduced['ref']
	for sample in samples[1:]:
		selection = selection & (reduced[sample] != reduced['ref'])

	selection = selection[selection]
	mutations = reduced.loc[selection.index]

	mutations = mutations[mutations['presentIn'] == len(samples)]['description']
	mutation_list = mutations.dropna().tolist()
	mutation_list = [i for i in mutation_list if i]
	if len(mutation_list) > 20:
		mutation_list = mutation_list[:20] + [f"+{len(mutation_list) - 20} more"]
	return mutation_list

def add_common_mutations_to_tree(comparison_table:pandas.DataFrame, tree:Tree):
	seen = list()
	for node in tree.traverse('preorder'):
		if not node.name:
			leafs = [i.name for i in node if i.name != 'reference']
			common_mutations = get_common_mutations(comparison_table, leafs)
			common_mutations = [i for i in common_mutations if i not in seen]
			common_mutations = [i for i in common_mutations if i.strip()]
			seen += common_mutations

			node.add_features(mutations = common_mutations)
			node.name = common_mutations
			tx = TextFace("\n".join(common_mutations))
			node.add_face(tx, column = 0, position = "branch-top")

if __name__ == "__main__":
	args = create_parser().parse_args()

	comparison_table = pandas.read_excel(args.filename, sheet_name = 'variant comparison')
	tree_filename = args.tree

	tree = Tree(tree_filename.read_text())

	add_common_mutations_to_tree(comparison_table, tree)

	tree.render(args.output)