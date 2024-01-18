import sys
import os
import logging
import argparse

from module_base.parameter import Parameter

from module_base.rc_module import RCModule
from modules.extract_images.extract_images import ExtractImages
from modules.georeference.georeference_images import GeoreferenceImages
from modules.image_batcher.batch_directory import BatchDirectory

def intialize_logger() -> logging.Logger:
	logging.basicConfig(level=logging.INFO)
	logger = logging.getLogger(__name__)

	return logger

def initialize_modules(logger) -> dict[str, RCModule]:
	"""
	Initializes the modules and returns a dict of the active modules.
	"""
	modules: dict[str, RCModule] = {}

	extract_images_module: ExtractImages = ExtractImages(logger)
	modules[extract_images_module.get_name()] = extract_images_module

	georeference_module: GeoreferenceImages = GeoreferenceImages(logger)
	modules[georeference_module.get_name()] = georeference_module

	batch_directory_module: BatchDirectory = BatchDirectory(logger)
	modules[batch_directory_module.get_name()] = batch_directory_module

	return modules

def initialize_parameters(modules) -> dict[str, Parameter]:
	"""
	Initializes the parameters and returns a dict of the active parameters.
	"""
	params: dict[str, Parameter] = {}

	# Global Parameters
	params['output_dir'] = Parameter(
		name='Output Directory',
		cli_short='o',
		cli_long='output_dir',
		type=str,
		default_value=None,
		description='Path to the output directory',
		prompt_user=True
	)

	params['continue_automatically'] = Parameter(
		name='Continue Automatically',
		cli_short='c',
		cli_long='continue_automatically',
		type=bool,
		default_value=False,
		description='Whether to continue automatically after each module',
		prompt_user=True
	)

	for module in modules.values():
		for param_name, param in module.get_parameters().items():
			if param.disable_when_module_active is not None and param.disable_when_module_active in modules:
				continue

			params[param_name] = param

	return params

def parse_arguments(argv, params, logger) -> dict[str, dict[str, object]]:
	"""
	Parses the command line arguments and prompts the user for any missing values.
	"""
	parser = argparse.ArgumentParser()
	
	for param in params.values():
		parser.add_argument(f'-{param.cli_short}', f'--{param.cli_long}', type=param.get_type(), help=param.get_description())

	args = parser.parse_args()

	for param in params.values():
		# if it's not specified in the command line arguments and prompt_user is true, prompt the user for the value
		if getattr(args, param.cli_long) is None and param.prompt_user:
			try:
				setattr(args, param.cli_long, param.get_type()(input(f'{param.get_description()}: ')))
			except ValueError:
				logger.warning(f'Invalid value for {param.get_name()}, using default value: {param.get_default_value()}')
				setattr(args, param.cli_long, param.get_default_value())

		# if it's not specified in the command line arguments and prompt_user is false, set the default value
		if getattr(args, param.cli_long) is None and not param.prompt_user:
			setattr(args, param.cli_long, param.get_default_value())

		# set the value in the params dict
		param.set_value(getattr(args, param.cli_long))

def update_parameters(params, modules) -> None:
	"""
	Updates the parameters of the modules with the values from the params dict.
	"""
	for module in modules.values():
		module.set_params(params)

def main(argv):
	# Initialize logger and modules
	logger = intialize_logger()
	modules: dict[str, RCModule] = initialize_modules(logger)

	# Initialize parameters
	params = initialize_parameters(modules)
	parse_arguments(argv, params, logger)
	update_parameters(params, modules)

	# Print parameters
	logger.info("Parameters:")
	for param_name, param in params.items():
		logger.info(f'{param_name} ({param.cli_short}): {param.get_value()}')

	# Run modules
	for index, module in enumerate(modules.values()):
		success, message = module.validate_parameters()

		if not success:
			logger.error(message)
			return
		
		logger.info(f'Running module: {module.get_name()}')
		module.run()
		module.finish()
		logger.info(f'Finished running module: {module.get_name()}')

		# if continue_automatically is false and it's not the last module, wait for user input
		if not params["continue_automatically"].get_value() and index != len(modules) - 1:
			input("Press enter to continue...")

if __name__ == '__main__':
	main(sys.argv)