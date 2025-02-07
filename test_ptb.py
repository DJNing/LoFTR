import pytorch_lightning as pl
import argparse
import pprint
from loguru import logger as loguru_logger

from src.config.default import get_cfg_defaults
from src.utils.profiler import build_profiler

from src.lightning.data import MultiSceneDataModule
from src.lightning.lightning_loftr import PL_LoFTR
import pdb
from torch import distributed as dist


if __name__ == '__main__':
        # init a costum parser which will be added into pl.Trainer parser
    # check documentation: https://pytorch-lightning.readthedocs.io/en/latest/common/trainer.html#trainer-flags
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument(
        '--ckpt_path', type=str, default="weights/indoor_ds.ckpt", help='path to the checkpoint')
    parser.add_argument(
        '--dump_dir', type=str, default=None, help="if set, the matching results will be dump to dump_dir")
    parser.add_argument(
        '--profiler_name', type=str, default=None, help='options: [inference, pytorch], or leave it unset')
    parser.add_argument(
        '--batch_size', type=int, default=1, help='batch_size per gpu')
    parser.add_argument(
        '--num_workers', type=int, default=2)
    parser.add_argument(
        '--thr', type=float, default=None, help='modify the coarse-level matching threshold.')

    parser = pl.Trainer.add_argparse_args(parser)
    # parse arguments

    args = parser.parse_args()

    args.data_cfg_path = 'configs/data/scannet_test_1500.py'
    args.main_cfg_path = 'configs/loftr/indoor/scannet/loftr_ds_eval.py'
    args.dump_dir = 'dump/loftr_ds_indoor'
    args.profiler_name = 'inference'
    args.num_nodes = 1
    args.gpu = 1
    args.torch_num_workers = 4
    args.accelerator = 'ddp'
    #args.accelerator = 'cpu'
    pprint.pprint(vars(args))
    
    # init default-cfg and merge it with the main- and data-cfg
    config = get_cfg_defaults()
    config.merge_from_file(args.main_cfg_path)
    config.merge_from_file(args.data_cfg_path)
    pl.seed_everything(config.TRAINER.SEED)  # reproducibility

    # tune when testing
    if args.thr is not None:
        config.LOFTR.MATCH_COARSE.THR = args.thr

    loguru_logger.info("Args and config initialized!")

    # lightning module
    profiler = build_profiler(args.profiler_name)
    model = PL_LoFTR(config, pretrained_ckpt=args.ckpt_path, profiler=profiler, dump_dir=args.dump_dir)
    loguru_logger.info("LoFTR-lightning initialized!")
    dist.init_process_group(backend='nccl', init_method='tcp://127.0.0.1:23452', rank=0, world_size=1)

    # lightning data
    data_module = MultiSceneDataModule(args, config)
    loguru_logger.info("DataModule initialized!")

    # lightning trainer
    trainer = pl.Trainer.from_argparse_args(args, replace_sampler_ddp=False, logger=False)

    #p.db.set_trace()
    loguru_logger.info("Start testing!")
    trainer.test(model, datamodule=data_module, verbose=False)
