import argparse
import os
from glob import glob
import cv2
import tensorflow as tf

from src.model.train_model import Trainer
from src.data.dataloader import DataLoader
from src.model.predict_model import predict
from src.visualization.visualize import Visualize
from src.config import config


def make_parser():
    parser = argparse.ArgumentParser("Image Classifier with Keras")

    parser.add_argument("--data_path", required=True, type=str, help="the raw data path")

    parser.add_argument("--batch_size", default=90, type=int, help="batch size")
    parser.add_argument("--img_size", default=(256, 256), help="the image size")
    parser.add_argument("--pretrained", default=None, type=str, help="the path of pretrained model")
    parser.add_argument("--ckpt_path", default="./save_ckpt/", type=str, help="the path of checkpoint")
    parser.add_argument("--train_learning_rate", default=0.001, type=float, help="the learning rate for training")
    parser.add_argument("--tune_learning_rate", default=1e-5, type=float, help="the learning rate for tuning")
    parser.add_argument("--train_epochs", default=5, type=int, help="the number epochs to train")
    parser.add_argument("--tune_epochs", default=20, type=int, help="the number epochs to tune")

    parser.add_argument("--convert2tflite", action="store_true", help="the model is to convert tflite model")

    parser.add_argument("--predict_data", type=str, help="the predict data path")
    parser.add_argument("--predict", action="store_true", help="the mode is to predict result")

    parser.add_argument("--predict_only", action="store_true", help="the mode is to predict result only")

    return parser


if __name__ == "__main__":
    physical_devices = tf.config.experimental.list_physical_devices('GPU')
    # physical_devices = tf.config.experimental.list_physical_devices('CPU')
    print("physical_devices-------------", len(physical_devices))
    tf.config.experimental.set_memory_growth(physical_devices[0], True)

    args = make_parser().parse_args()
    # Load data
    label2id = config.label2id
    print("\n Loading data" + "." * 10)
    dataloader = DataLoader(data_path=args.data_path,
                            label2id=label2id,
                            batch_size=args.batch_size,
                            img_size=args.img_size)
    train_generator, test_generator = dataloader.load_dataset()

    # training
    trainer = Trainer(img_size=args.img_size,
                      num_classes=len(label2id),
                      pretrained=args.pretrained,
                      ckpt_path=args.ckpt_path,
                      train_learning_rate=args.train_learning_rate,
                      tune_learning_rate=args.tune_learning_rate,
                      train_generator=train_generator,
                      test_generator=test_generator,
                      train_epochs=args.train_epochs,
                      tune_epochs=args.tune_epochs,
                      steps_per_epoch=dataloader.length_train//args.batch_size,
                      validation_steps=dataloader.length_val//args.batch_size)
    print("\n Training" + "." * 10)
    trainer.__call__()

    # evaluate
    print("\n Evaluating" + "." * 10)
    trainer.evaluate()

    # predict
    list_pred_img = []
    list_pred_array = []
    list_true_label = []
    if args.predict and os.path.exists(args.predict_data):
        print("\n Predicting" + "." * 10)
        for pred_path in glob(f"{args.predict_date}/*"):
            true_label = os.path.basename(pred_path)[:-4]
            list_true_label.append(true_label)

            pd_input = cv2.imread(pred_path)
            list_pred_img.append(pd_input)

            output = predict(pd_input, args.img_size, trainer.model)
            list_pred_array.append(output)

    # visualize
    visualize = Visualize(list_pred_array=list_pred_array,
                          list_true_label=list_true_label,
                          list_pd_img=list_pred_img,
                          class_names=list(label2id.keys()))

    # convert to tflite model
    if args.convert2tflite:
        trainer.convert_to_tflite()
        trainer.check_tflite_model()
