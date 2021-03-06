from jinja2 import Environment, PackageLoader, select_autoescape
import os
import tempfile
import sys
import extract_people as detect
import recognize_people as rec
import argparse
import contextlib
import shutil


def gen_HTML(filename, men_pc, ages, time_arr, attention_arr):
    j2_env = Environment(
        loader=PackageLoader('boremeter', 'templates'),
        autoescape=select_autoescape(['html'])
    )
    template = j2_env.get_template('report.html')

    with open(filename, "wb") as fh:
        fh.write(template.render(men_pc=men_pc, 
            ages=str(ages.tolist()), 
            time_arr=str(time_arr.tolist()),
            attention_arr=str(attention_arr.tolist())))


@contextlib.contextmanager
def temporary_directory(*args, **kwargs):
    d = tempfile.mkdtemp(*args, **kwargs)
    try:
        yield d
    finally:
        shutil.rmtree(d)

def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--file', type=argparse.FileType('r'), help='input video file', required=True)
    parser.add_argument('--frames_limit', default=200, type=int, help='limit of frames to process > 2')
    parser.add_argument('--output_html', default='report.html', type=argparse.FileType('w'),
        help='path to output .html file with report')
    parser.add_argument('--output_video', default=None, type=argparse.FileType('w'),
        help='path to output .avi file with visualisation of bounding boxes')
    parser.add_argument('--output_csv', default='recognized.csv', type=argparse.FileType('w'),
        help='path to output table with information about all detected faces')
    parser.add_argument('--caffe_models_path', default='/root/caffe/models', type=str, 
        help='path to directory with pre-trained models must contain "age.prototxt", "gender.prototxt",'
             '"age.caffemodel", "gender.caffemodel"')
    args = parser.parse_args()

    if args.frames_limit < 3:
        raise argparse.ArgumentTypeError("minimum frames_limit is 3")

    caffe_models_path = os.environ.get('CAFFE_MODELS_PATH') or args.caffe_models_path

    # Constant parameters (where to put them???)
    # I am not sure, maybe they should be cmdline flags too
    DETECTION_STEP = 5
    RECOGNITION_STEP = DETECTION_STEP * 6  # recognition_step % detection_step == 0 must be True

    # create temporary directory in the current directory where cropped faces will be stored
    with temporary_directory() as tmp_dir:

        print ("Extracting people.....")
        detect.fast_extract(args.file.name, visualize=args.output_video is not None, frames_limit=args.frames_limit,
                            tmp_dir=tmp_dir, detection_step=DETECTION_STEP, output_videofile=args.output_video)

        print ("Extracting statistics.....")
        detected_faces_df = rec.recognize_people(tmp_dir=tmp_dir, frames_limit=args.frames_limit, 
                                                 caffe_models_path=caffe_models_path, recognition_step=RECOGNITION_STEP)
        detected_faces_df.to_csv(args.output_csv.name)

        print ("Generating html.....")
        men_pc, ages, frames_id, attention_pc = rec.get_stats(detected_faces_df)
        gen_HTML(args.output_html.name, men_pc, ages, frames_id, attention_pc)


if __name__ == "__main__":
    main()


