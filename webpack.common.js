const path = require("path");
const glob = require("glob");

let globPath = './**/entry/*.js';
let filePath = glob.sync(globPath)
//入口配置
let entries = {};
//出口目录
let outputsPath = './static/farm_output';
for (let i = 0; i < filePath.length; i++) {
    let fpath = filePath[i];
    let fileName = fpath.split('/')[fpath.split('/').length - 1];
    let entryName = fileName.split('.')[0];
    entries[entryName] = fpath;
}
let config = {
    entry: entries,
    output: {
        path: path.resolve(__dirname, outputsPath),
        filename: '[name].js',
        // chunkFilename: "[name]-[hash:5].chunk.js"
        chunkFilename: "[name].chunk.js"
    },
    module: {
        rules: [
            {
                test: /\.js$||\.jsx?/,
                exclude: /node_modules/,
                loader: 'babel-loader',
                options: {
                    presets: ['es2015', 'react'],
                    plugins: [
                        ["import", {
                            "libraryName": "antd",
                            "libraryDirectory": "es",
                            "style": "css"
                        }]
                    ]
                },
            },
            {
                test: /\.(sa|sc|c)ss$/,
                use: [
                    'style-loader',
                    'css-loader',
                    'sass-loader',
                ],
            },
            {
                //配置antd主题色 页面中需要 // import 'antd/dist/antd.less';
                test: /\.less$/,
                use: [
                    {loader: 'style-loader'},
                    {loader: 'css-loader'},
                    {
                        loader: 'less-loader',
                        options: {
                            modifyVars: {
                                'primary-color': '#2161fd',
                                'border-color-base': '#e4e6ea',
                                'border-radius-base': '2px',
                                'box-shadow-base': '0 2px 16px 0 rgba(33, 43, 54, 0.08), 0 1px 3px 0 rgba(64, 66, 69, 0.12), 0 0 0 1px rgba(78, 84, 96, 0.1);',
                            },
                            javascriptEnabled: true,
                        }
                    },
                ],
            },
            {
                test: /\.(png|jpg|gif|jpeg|svg)$/,
                use: [
                    {
                        loader: "url-loader",
                        options: {
                            // name: "[name].[hash:5].[ext]",
                            // limit: 1024, // size <= 1kib
                            // outputPath: "img"
                        }
                    }
                ]
            }
        ],
    },
    plugins: [],
    resolve: {
        alias: {
            '@components': path.resolve(__dirname, './farmbase/static/components'),
        }
    },
}

module.exports = config;

